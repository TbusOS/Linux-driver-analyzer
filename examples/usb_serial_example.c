/*
 * USB串口驱动示例
 * 
 * 这是一个简化的USB转串口驱动
 * 演示了批量传输和tty层接口
 */

#include <linux/kernel.h>
#include <linux/errno.h>
#include <linux/slab.h>
#include <linux/tty.h>
#include <linux/tty_driver.h>
#include <linux/tty_flip.h>
#include <linux/module.h>
#include <linux/spinlock.h>
#include <linux/mutex.h>
#include <linux/usb.h>
#include <linux/usb/serial.h>
#include <linux/serial.h>
#include <linux/kfifo.h>

/* 定义厂商ID和产品ID（示例：FTDI芯片）*/
#define VENDOR_ID  0x0403
#define PRODUCT_ID 0x6001

/* 缓冲区大小 */
#define SERIAL_BUF_SIZE  256

/* 串口私有数据 */
struct usb_serial_private {
    spinlock_t lock;
    struct usb_device *udev;
    struct usb_interface *interface;
    struct tty_struct *tty;
    struct urb *read_urb;
    struct urb *write_urb;
    unsigned char *bulk_in_buffer;
    unsigned char *bulk_out_buffer;
    size_t bulk_in_size;
    size_t bulk_out_size;
    __u8 bulk_in_endpointAddr;
    __u8 bulk_out_endpointAddr;
    struct kfifo write_fifo;
    struct work_struct work;
    int open_count;
    struct mutex mutex;
};

/* 前向声明 */
static struct usb_driver usb_serial_driver;
static struct tty_driver *serial_tty_driver;

/* 读URB完成处理 */
static void serial_read_bulk_callback(struct urb *urb)
{
    struct usb_serial_private *priv = urb->context;
    struct tty_struct *tty;
    unsigned char *data = urb->transfer_buffer;
    int status = urb->status;
    int result;
    int i;
    
    /* 检查状态 */
    if (status) {
        if (status == -ENOENT ||
            status == -ECONNRESET ||
            status == -ESHUTDOWN) {
            /* URB被终止 */
            return;
        } else {
            dev_err(&priv->interface->dev,
                    "读URB错误: %d\n", status);
            goto resubmit;
        }
    }
    
    /* 处理接收到的数据 */
    tty = priv->tty;
    if (tty && urb->actual_length) {
        /* 将数据推送到tty层 */
        for (i = 0; i < urb->actual_length; i++) {
            if (!tty_insert_flip_char(&tty->port, data[i], TTY_NORMAL)) {
                dev_err(&priv->interface->dev, "TTY缓冲区满\n");
                break;
            }
        }
        tty_flip_buffer_push(&tty->port);
    }
    
resubmit:
    /* 重新提交URB */
    result = usb_submit_urb(urb, GFP_ATOMIC);
    if (result)
        dev_err(&priv->interface->dev,
                "重新提交读URB失败: %d\n", result);
}

/* 写URB完成处理 */
static void serial_write_bulk_callback(struct urb *urb)
{
    struct usb_serial_private *priv = urb->context;
    unsigned long flags;
    
    /* 检查状态 */
    if (urb->status) {
        dev_err(&priv->interface->dev,
                "写URB错误: %d\n", urb->status);
    }
    
    /* 调度工作队列继续发送 */
    schedule_work(&priv->work);
}

/* 工作队列处理函数 */
static void serial_send_work(struct work_struct *work)
{
    struct usb_serial_private *priv = 
        container_of(work, struct usb_serial_private, work);
    unsigned long flags;
    int count;
    int result;
    
    spin_lock_irqsave(&priv->lock, flags);
    
    /* 检查是否有数据要发送 */
    if (priv->write_urb->status == -EINPROGRESS) {
        spin_unlock_irqrestore(&priv->lock, flags);
        return;
    }
    
    count = kfifo_out(&priv->write_fifo, 
                      priv->bulk_out_buffer,
                      priv->bulk_out_size);
    
    if (count == 0) {
        spin_unlock_irqrestore(&priv->lock, flags);
        return;
    }
    
    /* 准备URB */
    priv->write_urb->transfer_buffer_length = count;
    
    spin_unlock_irqrestore(&priv->lock, flags);
    
    /* 提交URB */
    result = usb_submit_urb(priv->write_urb, GFP_KERNEL);
    if (result) {
        dev_err(&priv->interface->dev,
                "提交写URB失败: %d\n", result);
    }
}

/* TTY打开 */
static int serial_open(struct tty_struct *tty, struct file *filp)
{
    struct usb_serial_private *priv;
    int index = tty->index;
    int result = 0;
    
    /* 查找对应的USB设备 */
    priv = tty->driver_data;
    if (!priv)
        return -ENODEV;
    
    mutex_lock(&priv->mutex);
    
    /* 增加打开计数 */
    priv->open_count++;
    if (priv->open_count == 1) {
        /* 第一次打开 */
        priv->tty = tty;
        
        /* 提交读URB */
        usb_fill_bulk_urb(priv->read_urb, priv->udev,
                         usb_rcvbulkpipe(priv->udev, priv->bulk_in_endpointAddr),
                         priv->bulk_in_buffer,
                         priv->bulk_in_size,
                         serial_read_bulk_callback, priv);
        
        result = usb_submit_urb(priv->read_urb, GFP_KERNEL);
        if (result) {
            dev_err(&priv->interface->dev,
                    "提交读URB失败: %d\n", result);
            priv->open_count--;
            priv->tty = NULL;
        }
    }
    
    mutex_unlock(&priv->mutex);
    
    return result;
}

/* TTY关闭 */
static void serial_close(struct tty_struct *tty, struct file *filp)
{
    struct usb_serial_private *priv = tty->driver_data;
    
    if (!priv)
        return;
    
    mutex_lock(&priv->mutex);
    
    priv->open_count--;
    if (priv->open_count == 0) {
        /* 最后一次关闭 */
        
        /* 停止URB */
        usb_kill_urb(priv->read_urb);
        usb_kill_urb(priv->write_urb);
        
        /* 取消工作队列 */
        cancel_work_sync(&priv->work);
        
        priv->tty = NULL;
    }
    
    mutex_unlock(&priv->mutex);
}

/* TTY写入 */
static int serial_write(struct tty_struct *tty,
                       const unsigned char *buf, int count)
{
    struct usb_serial_private *priv = tty->driver_data;
    unsigned long flags;
    int retval;
    
    if (!priv)
        return -ENODEV;
    
    spin_lock_irqsave(&priv->lock, flags);
    
    /* 将数据加入FIFO */
    retval = kfifo_in(&priv->write_fifo, buf, count);
    
    spin_unlock_irqrestore(&priv->lock, flags);
    
    /* 触发发送 */
    schedule_work(&priv->work);
    
    return retval;
}

/* TTY写入空间 */
static int serial_write_room(struct tty_struct *tty)
{
    struct usb_serial_private *priv = tty->driver_data;
    unsigned long flags;
    int room;
    
    if (!priv)
        return 0;
    
    spin_lock_irqsave(&priv->lock, flags);
    room = kfifo_avail(&priv->write_fifo);
    spin_unlock_irqrestore(&priv->lock, flags);
    
    return room;
}

/* TTY操作结构 */
static const struct tty_operations serial_ops = {
    .open = serial_open,
    .close = serial_close,
    .write = serial_write,
    .write_room = serial_write_room,
};

/* USB探测函数 */
static int usb_serial_probe(struct usb_interface *interface,
                          const struct usb_device_id *id)
{
    struct usb_serial_private *priv;
    struct usb_host_interface *iface_desc;
    struct usb_endpoint_descriptor *endpoint;
    struct usb_device *udev = interface_to_usbdev(interface);
    int i;
    int retval = -ENOMEM;
    
    /* 分配私有数据 */
    priv = kzalloc(sizeof(*priv), GFP_KERNEL);
    if (!priv)
        return -ENOMEM;
    
    /* 初始化 */
    spin_lock_init(&priv->lock);
    mutex_init(&priv->mutex);
    priv->udev = usb_get_dev(udev);
    priv->interface = interface;
    INIT_WORK(&priv->work, serial_send_work);
    
    /* 解析端点 */
    iface_desc = interface->cur_altsetting;
    for (i = 0; i < iface_desc->desc.bNumEndpoints; i++) {
        endpoint = &iface_desc->endpoint[i].desc;
        
        if (usb_endpoint_is_bulk_in(endpoint)) {
            priv->bulk_in_size = usb_endpoint_maxp(endpoint);
            priv->bulk_in_endpointAddr = endpoint->bEndpointAddress;
            priv->bulk_in_buffer = kmalloc(priv->bulk_in_size, GFP_KERNEL);
            if (!priv->bulk_in_buffer)
                goto error;
        }
        
        if (usb_endpoint_is_bulk_out(endpoint)) {
            priv->bulk_out_size = usb_endpoint_maxp(endpoint);
            priv->bulk_out_endpointAddr = endpoint->bEndpointAddress;
            priv->bulk_out_buffer = kmalloc(priv->bulk_out_size, GFP_KERNEL);
            if (!priv->bulk_out_buffer)
                goto error;
        }
    }
    
    if (!priv->bulk_in_endpointAddr || !priv->bulk_out_endpointAddr) {
        dev_err(&interface->dev, "找不到批量端点\n");
        retval = -ENODEV;
        goto error;
    }
    
    /* 分配URB */
    priv->read_urb = usb_alloc_urb(0, GFP_KERNEL);
    if (!priv->read_urb)
        goto error;
    
    priv->write_urb = usb_alloc_urb(0, GFP_KERNEL);
    if (!priv->write_urb)
        goto error;
    
    /* 初始化写URB */
    usb_fill_bulk_urb(priv->write_urb, priv->udev,
                     usb_sndbulkpipe(priv->udev, priv->bulk_out_endpointAddr),
                     priv->bulk_out_buffer,
                     priv->bulk_out_size,
                     serial_write_bulk_callback, priv);
    
    /* 初始化FIFO */
    retval = kfifo_alloc(&priv->write_fifo, SERIAL_BUF_SIZE, GFP_KERNEL);
    if (retval)
        goto error;
    
    /* 保存设备数据 */
    usb_set_intfdata(interface, priv);
    
    /* 注册TTY设备 */
    /* 这里简化处理，实际应该动态分配TTY设备号 */
    
    dev_info(&interface->dev, "USB串口设备已连接\n");
    
    return 0;
    
error:
    if (priv) {
        usb_free_urb(priv->read_urb);
        usb_free_urb(priv->write_urb);
        kfree(priv->bulk_in_buffer);
        kfree(priv->bulk_out_buffer);
        kfifo_free(&priv->write_fifo);
        usb_put_dev(priv->udev);
        kfree(priv);
    }
    return retval;
}

/* USB断开函数 */
static void usb_serial_disconnect(struct usb_interface *interface)
{
    struct usb_serial_private *priv = usb_get_intfdata(interface);
    
    if (!priv)
        return;
    
    /* 停止所有传输 */
    usb_kill_urb(priv->read_urb);
    usb_kill_urb(priv->write_urb);
    cancel_work_sync(&priv->work);
    
    /* 清理资源 */
    usb_free_urb(priv->read_urb);
    usb_free_urb(priv->write_urb);
    kfree(priv->bulk_in_buffer);
    kfree(priv->bulk_out_buffer);
    kfifo_free(&priv->write_fifo);
    usb_put_dev(priv->udev);
    
    usb_set_intfdata(interface, NULL);
    kfree(priv);
    
    dev_info(&interface->dev, "USB串口设备已断开\n");
}

/* USB设备ID表 */
static const struct usb_device_id usb_serial_id_table[] = {
    { USB_DEVICE(VENDOR_ID, PRODUCT_ID) },
    { }  /* 终止符 */
};
MODULE_DEVICE_TABLE(usb, usb_serial_id_table);

/* USB驱动结构 */
static struct usb_driver usb_serial_driver = {
    .name       = "usb_serial_example",
    .probe      = usb_serial_probe,
    .disconnect = usb_serial_disconnect,
    .id_table   = usb_serial_id_table,
};

/* 模块初始化 */
static int __init usb_serial_init(void)
{
    int retval;
    
    /* 分配TTY驱动 */
    serial_tty_driver = alloc_tty_driver(256);
    if (!serial_tty_driver)
        return -ENOMEM;
    
    /* 设置TTY驱动 */
    serial_tty_driver->driver_name = "usb_serial";
    serial_tty_driver->name = "ttyUSB";
    serial_tty_driver->major = 0;  /* 动态分配 */
    serial_tty_driver->minor_start = 0;
    serial_tty_driver->type = TTY_DRIVER_TYPE_SERIAL;
    serial_tty_driver->subtype = SERIAL_TYPE_NORMAL;
    serial_tty_driver->flags = TTY_DRIVER_REAL_RAW | TTY_DRIVER_DYNAMIC_DEV;
    serial_tty_driver->init_termios = tty_std_termios;
    serial_tty_driver->init_termios.c_cflag = B9600 | CS8 | CREAD | HUPCL | CLOCAL;
    tty_set_operations(serial_tty_driver, &serial_ops);
    
    /* 注册TTY驱动 */
    retval = tty_register_driver(serial_tty_driver);
    if (retval) {
        put_tty_driver(serial_tty_driver);
        return retval;
    }
    
    /* 注册USB驱动 */
    retval = usb_register(&usb_serial_driver);
    if (retval) {
        tty_unregister_driver(serial_tty_driver);
        put_tty_driver(serial_tty_driver);
        return retval;
    }
    
    pr_info("USB串口驱动已加载\n");
    return 0;
}

/* 模块退出 */
static void __exit usb_serial_exit(void)
{
    /* 注销USB驱动 */
    usb_deregister(&usb_serial_driver);
    
    /* 注销TTY驱动 */
    tty_unregister_driver(serial_tty_driver);
    put_tty_driver(serial_tty_driver);
    
    pr_info("USB串口驱动已卸载\n");
}

module_init(usb_serial_init);
module_exit(usb_serial_exit);

MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("USB串口驱动示例");
MODULE_LICENSE("GPL");
