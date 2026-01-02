/**
 * advanced_driver.c - 高级特性示例驱动
 * 
 * 这个示例展示了 v0.2 tree-sitter 后端相比 v0.1 regex 后端的增强功能：
 * - 枚举 (enum) 定义提取
 * - 联合体 (union) 定义提取
 * - 函数声明（非定义）识别
 * - 精确的位置信息（列号、结束位置）
 * - typedef 内部定义的类型提取
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/usb.h>
#include <linux/slab.h>
#include <linux/workqueue.h>

/* ============== 枚举定义 ============== */

/* 设备状态枚举 */
enum device_state {
    STATE_IDLE = 0,
    STATE_CONNECTING,
    STATE_CONNECTED,
    STATE_TRANSFERRING,
    STATE_ERROR = -1
};

/* 命令类型枚举 */
enum cmd_type {
    CMD_READ = 0x01,
    CMD_WRITE = 0x02,
    CMD_CONTROL = 0x03,
    CMD_STATUS = 0x04,
    CMD_RESET = 0xFF
};

/* 使用 typedef 的枚举 */
typedef enum {
    RESULT_OK = 0,
    RESULT_BUSY = -EBUSY,
    RESULT_NOMEM = -ENOMEM,
    RESULT_INVALID = -EINVAL
} result_t;

/* ============== 联合体定义 ============== */

/* 数据包联合体 - 不同视图访问同一数据 */
union data_packet {
    uint8_t  bytes[64];
    uint16_t words[32];
    uint32_t dwords[16];
    uint64_t qwords[8];
    struct {
        uint8_t header[4];
        uint8_t payload[60];
    } frame;
};

/* 寄存器联合体 */
union control_reg {
    uint32_t raw;
    struct {
        uint32_t enable     : 1;
        uint32_t direction  : 1;
        uint32_t speed      : 2;
        uint32_t mode       : 4;
        uint32_t reserved   : 24;
    } bits;
};

/* ============== 结构体定义 ============== */

/* 设备配置结构体 */
struct device_config {
    char name[32];
    int timeout_ms;
    int retry_count;
    bool auto_reconnect;
};

/* 主设备结构体 - 包含各种类型引用 */
struct advanced_device {
    /* 基本信息 */
    struct usb_device *udev;
    struct usb_interface *interface;
    spinlock_t lock;
    
    /* 状态信息 */
    enum device_state state;
    result_t last_result;
    
    /* 数据缓冲区 */
    union data_packet tx_buffer;
    union data_packet rx_buffer;
    
    /* 控制寄存器 */
    union control_reg ctrl;
    
    /* 配置 */
    struct device_config config;
    struct device_config *config_ptr;
    
    /* 端点信息 */
    __u8 bulk_in_addr;
    __u8 bulk_out_addr;
    size_t bulk_in_size;
    
    /* URB */
    struct urb *ctrl_urb;
    struct urb *bulk_urb;
    
    /* 工作队列 */
    struct work_struct work;
    struct delayed_work delayed_work;
    
    /* 回调函数指针 */
    void (*on_connect)(struct advanced_device *dev);
    void (*on_disconnect)(struct advanced_device *dev);
    int (*on_data)(struct advanced_device *dev, void *data, size_t len);
};

/* typedef 结构体 */
typedef struct {
    int x;
    int y;
    int z;
} point3d_t;

/* ============== 函数声明（非定义） ============== */

/* 这些函数声明会被 v0.2 识别，但 v0.1 不会 */
static int device_open(struct inode *inode, struct file *file);
static int device_release(struct inode *inode, struct file *file);
static ssize_t device_read(struct file *file, char __user *buf, 
                           size_t count, loff_t *pos);
static ssize_t device_write(struct file *file, const char __user *buf,
                            size_t count, loff_t *pos);
static int send_command(struct advanced_device *dev, enum cmd_type cmd, 
                        void *data, size_t len);
static result_t process_response(struct advanced_device *dev, 
                                 union data_packet *packet);

/* ============== 回调处理函数 ============== */

static void bulk_complete_callback(struct urb *urb)
{
    struct advanced_device *dev = urb->context;
    
    if (!dev)
        return;
    
    switch (urb->status) {
    case 0:
        dev->state = STATE_IDLE;
        dev->last_result = RESULT_OK;
        if (dev->on_data)
            dev->on_data(dev, urb->transfer_buffer, urb->actual_length);
        break;
    case -ENOENT:
    case -ECONNRESET:
    case -ESHUTDOWN:
        dev->state = STATE_ERROR;
        break;
    default:
        dev->state = STATE_ERROR;
        dev->last_result = RESULT_INVALID;
        break;
    }
}

static void ctrl_complete_callback(struct urb *urb)
{
    struct advanced_device *dev = urb->context;
    
    if (!dev)
        return;
    
    if (urb->status == 0) {
        union control_reg *reg = urb->transfer_buffer;
        dev->ctrl.raw = reg->raw;
    }
}

/* ============== 工作队列处理 ============== */

static void device_work_handler(struct work_struct *work)
{
    struct advanced_device *dev = container_of(work, struct advanced_device, work);
    
    spin_lock(&dev->lock);
    
    if (dev->state == STATE_CONNECTED) {
        /* 发送状态查询命令 */
        send_command(dev, CMD_STATUS, NULL, 0);
    }
    
    spin_unlock(&dev->lock);
}

static void device_delayed_work_handler(struct work_struct *work)
{
    struct advanced_device *dev = container_of(work, struct advanced_device, 
                                               delayed_work.work);
    
    if (dev->state == STATE_ERROR && dev->config.auto_reconnect) {
        dev->state = STATE_CONNECTING;
        /* 尝试重连 */
        send_command(dev, CMD_RESET, NULL, 0);
    }
}

/* ============== 核心功能函数 ============== */

static int send_command(struct advanced_device *dev, enum cmd_type cmd,
                        void *data, size_t len)
{
    union data_packet *pkt = &dev->tx_buffer;
    
    if (!dev || dev->state == STATE_ERROR)
        return -EINVAL;
    
    /* 构建命令包 */
    memset(pkt, 0, sizeof(*pkt));
    pkt->frame.header[0] = 0xAA;  /* 同步字节 */
    pkt->frame.header[1] = cmd;
    pkt->frame.header[2] = len & 0xFF;
    pkt->frame.header[3] = (len >> 8) & 0xFF;
    
    if (data && len > 0 && len <= sizeof(pkt->frame.payload))
        memcpy(pkt->frame.payload, data, len);
    
    dev->state = STATE_TRANSFERRING;
    
    /* 提交 URB */
    usb_fill_bulk_urb(dev->bulk_urb,
                      dev->udev,
                      usb_sndbulkpipe(dev->udev, dev->bulk_out_addr),
                      pkt->bytes,
                      4 + len,
                      bulk_complete_callback,
                      dev);
    
    return usb_submit_urb(dev->bulk_urb, GFP_KERNEL);
}

static result_t process_response(struct advanced_device *dev,
                                 union data_packet *packet)
{
    enum cmd_type cmd;
    
    if (!packet)
        return RESULT_INVALID;
    
    /* 检查同步字节 */
    if (packet->frame.header[0] != 0xAA)
        return RESULT_INVALID;
    
    cmd = packet->frame.header[1];
    
    switch (cmd) {
    case CMD_READ:
    case CMD_WRITE:
        return RESULT_OK;
    case CMD_STATUS:
        dev->ctrl.raw = *(uint32_t *)packet->frame.payload;
        return RESULT_OK;
    case CMD_RESET:
        dev->state = STATE_IDLE;
        return RESULT_OK;
    default:
        return RESULT_INVALID;
    }
}

/* ============== 设备操作函数 ============== */

static int device_open(struct inode *inode, struct file *file)
{
    struct advanced_device *dev;
    
    dev = container_of(inode->i_cdev, struct advanced_device, /* cdev */);
    file->private_data = dev;
    
    spin_lock(&dev->lock);
    if (dev->state != STATE_IDLE) {
        spin_unlock(&dev->lock);
        return -EBUSY;
    }
    dev->state = STATE_CONNECTING;
    spin_unlock(&dev->lock);
    
    /* 调用连接回调 */
    if (dev->on_connect)
        dev->on_connect(dev);
    
    return 0;
}

static int device_release(struct inode *inode, struct file *file)
{
    struct advanced_device *dev = file->private_data;
    
    /* 调用断开回调 */
    if (dev->on_disconnect)
        dev->on_disconnect(dev);
    
    spin_lock(&dev->lock);
    dev->state = STATE_IDLE;
    spin_unlock(&dev->lock);
    
    return 0;
}

static ssize_t device_read(struct file *file, char __user *buf,
                           size_t count, loff_t *pos)
{
    struct advanced_device *dev = file->private_data;
    size_t to_copy;
    
    if (dev->state != STATE_CONNECTED)
        return -ENODEV;
    
    to_copy = min(count, sizeof(dev->rx_buffer));
    
    if (copy_to_user(buf, dev->rx_buffer.bytes, to_copy))
        return -EFAULT;
    
    return to_copy;
}

static ssize_t device_write(struct file *file, const char __user *buf,
                            size_t count, loff_t *pos)
{
    struct advanced_device *dev = file->private_data;
    size_t to_copy;
    int ret;
    
    if (dev->state != STATE_CONNECTED)
        return -ENODEV;
    
    to_copy = min(count, sizeof(dev->tx_buffer.frame.payload));
    
    if (copy_from_user(dev->tx_buffer.frame.payload, buf, to_copy))
        return -EFAULT;
    
    ret = send_command(dev, CMD_WRITE, NULL, to_copy);
    if (ret < 0)
        return ret;
    
    return to_copy;
}

/* ============== 文件操作结构体 ============== */

static const struct file_operations advanced_fops = {
    .owner = THIS_MODULE,
    .open = device_open,
    .release = device_release,
    .read = device_read,
    .write = device_write,
};

/* ============== USB 驱动回调 ============== */

static int advanced_probe(struct usb_interface *interface,
                          const struct usb_device_id *id)
{
    struct advanced_device *dev;
    struct usb_endpoint_descriptor *bulk_in, *bulk_out;
    int ret;
    
    dev = kzalloc(sizeof(*dev), GFP_KERNEL);
    if (!dev)
        return -ENOMEM;
    
    dev->udev = usb_get_dev(interface_to_usbdev(interface));
    dev->interface = interface;
    spin_lock_init(&dev->lock);
    dev->state = STATE_IDLE;
    
    /* 初始化默认配置 */
    strncpy(dev->config.name, "advanced_device", sizeof(dev->config.name) - 1);
    dev->config.timeout_ms = 1000;
    dev->config.retry_count = 3;
    dev->config.auto_reconnect = true;
    
    /* 初始化工作队列 */
    INIT_WORK(&dev->work, device_work_handler);
    INIT_DELAYED_WORK(&dev->delayed_work, device_delayed_work_handler);
    
    /* 分配 URB */
    dev->ctrl_urb = usb_alloc_urb(0, GFP_KERNEL);
    dev->bulk_urb = usb_alloc_urb(0, GFP_KERNEL);
    if (!dev->ctrl_urb || !dev->bulk_urb) {
        ret = -ENOMEM;
        goto error;
    }
    
    /* 查找端点 */
    ret = usb_find_common_endpoints(interface->cur_altsetting,
                                    &bulk_in, &bulk_out, NULL, NULL);
    if (ret) {
        dev_err(&interface->dev, "Could not find bulk endpoints\n");
        goto error;
    }
    
    dev->bulk_in_addr = bulk_in->bEndpointAddress;
    dev->bulk_out_addr = bulk_out->bEndpointAddress;
    dev->bulk_in_size = usb_endpoint_maxp(bulk_in);
    
    usb_set_intfdata(interface, dev);
    
    dev_info(&interface->dev, "Advanced device connected\n");
    return 0;
    
error:
    usb_free_urb(dev->ctrl_urb);
    usb_free_urb(dev->bulk_urb);
    usb_put_dev(dev->udev);
    kfree(dev);
    return ret;
}

static void advanced_disconnect(struct usb_interface *interface)
{
    struct advanced_device *dev = usb_get_intfdata(interface);
    
    if (!dev)
        return;
    
    usb_set_intfdata(interface, NULL);
    
    /* 取消工作队列 */
    cancel_work_sync(&dev->work);
    cancel_delayed_work_sync(&dev->delayed_work);
    
    /* 释放 URB */
    usb_kill_urb(dev->ctrl_urb);
    usb_kill_urb(dev->bulk_urb);
    usb_free_urb(dev->ctrl_urb);
    usb_free_urb(dev->bulk_urb);
    
    usb_put_dev(dev->udev);
    kfree(dev);
    
    dev_info(&interface->dev, "Advanced device disconnected\n");
}

/* ============== USB 驱动结构体 ============== */

static const struct usb_device_id advanced_id_table[] = {
    { USB_DEVICE(0x1234, 0x5678) },
    { }
};
MODULE_DEVICE_TABLE(usb, advanced_id_table);

static struct usb_driver advanced_driver = {
    .name = "advanced_driver",
    .probe = advanced_probe,
    .disconnect = advanced_disconnect,
    .id_table = advanced_id_table,
};

module_usb_driver(advanced_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Example Author");
MODULE_DESCRIPTION("Advanced Features Demo Driver for v0.2 Testing");

