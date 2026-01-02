/*
 * 异步处理机制演示驱动
 * 
 * 这是一个展示Linux内核各种异步处理机制的示例驱动
 * 包含：工作队列、定时器、中断、Tasklet、线程化中断等
 */

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/interrupt.h>
#include <linux/workqueue.h>
#include <linux/timer.h>
#include <linux/hrtimer.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/platform_device.h>

#define DRIVER_NAME "async_demo"
#define IRQ_NUM 42

/* 驱动私有数据 */
struct async_demo_dev {
    struct platform_device *pdev;
    
    /* 工作队列 */
    struct work_struct work;
    struct delayed_work delayed_work;
    
    /* Tasklet */
    struct tasklet_struct tasklet;
    
    /* 定时器 */
    struct timer_list timer;
    struct hrtimer hrtimer;
    
    /* 内核线程 */
    struct task_struct *kthread;
    struct completion thread_done;
    
    /* 中断 */
    int irq;
    
    /* 状态 */
    atomic_t running;
    spinlock_t lock;
};

static struct async_demo_dev *demo_dev;

/* ============ 工作队列处理 ============ */

static void demo_work_handler(struct work_struct *work)
{
    struct async_demo_dev *dev = container_of(work, struct async_demo_dev, work);
    
    pr_info("[工作队列] 开始处理 (进程上下文，可睡眠)\n");
    
    /* 可以安全地睡眠 */
    msleep(100);
    
    /* 可以使用互斥锁 */
    mutex_lock(&dev->pdev->dev.mutex);
    pr_info("[工作队列] 处理完成\n");
    mutex_unlock(&dev->pdev->dev.mutex);
}

static void demo_delayed_work_handler(struct work_struct *work)
{
    struct delayed_work *dwork = to_delayed_work(work);
    struct async_demo_dev *dev = container_of(dwork, struct async_demo_dev, delayed_work);
    
    pr_info("[延迟工作队列] 延迟后开始处理\n");
    
    /* 重新调度自己，实现周期性任务 */
    if (atomic_read(&dev->running))
        schedule_delayed_work(&dev->delayed_work, msecs_to_jiffies(1000));
}

/* ============ Tasklet处理 ============ */

static void demo_tasklet_handler(unsigned long data)
{
    struct async_demo_dev *dev = (struct async_demo_dev *)data;
    unsigned long flags;
    
    pr_info("[Tasklet] 软中断上下文处理 (不可睡眠)\n");
    
    /* 只能使用自旋锁 */
    spin_lock_irqsave(&dev->lock, flags);
    /* 快速处理 */
    spin_unlock_irqrestore(&dev->lock, flags);
    
    /* 触发工作队列进行耗时操作 */
    schedule_work(&dev->work);
}

/* ============ 定时器处理 ============ */

static void demo_timer_callback(struct timer_list *t)
{
    struct async_demo_dev *dev = from_timer(dev, t, timer);
    
    pr_info("[定时器] 到期回调 (软中断上下文)\n");
    
    /* 调度tasklet */
    tasklet_schedule(&dev->tasklet);
    
    /* 重新设置定时器 */
    if (atomic_read(&dev->running))
        mod_timer(&dev->timer, jiffies + msecs_to_jiffies(500));
}

static enum hrtimer_restart demo_hrtimer_callback(struct hrtimer *timer)
{
    struct async_demo_dev *dev = container_of(timer, struct async_demo_dev, hrtimer);
    
    pr_info("[高精度定时器] 纳秒级精度回调 (硬中断上下文)\n");
    
    /* 重新启动 */
    if (atomic_read(&dev->running)) {
        hrtimer_forward_now(timer, ms_to_ktime(100));
        return HRTIMER_RESTART;
    }
    
    return HRTIMER_NORESTART;
}

/* ============ 中断处理 ============ */

static irqreturn_t demo_irq_handler(int irq, void *dev_id)
{
    struct async_demo_dev *dev = dev_id;
    
    pr_info("[硬中断] 快速处理上半部\n");
    
    /* 中断上下文，必须快速返回 */
    /* 调度下半部处理 */
    tasklet_schedule(&dev->tasklet);
    
    return IRQ_HANDLED;
}

static irqreturn_t demo_irq_thread_handler(int irq, void *dev_id)
{
    struct async_demo_dev *dev = dev_id;
    
    pr_info("[线程化中断] 进程上下文处理下半部 (可睡眠)\n");
    
    /* 可以睡眠的耗时操作 */
    msleep(10);
    
    return IRQ_HANDLED;
}

/* ============ 内核线程 ============ */

static int demo_kthread_func(void *data)
{
    struct async_demo_dev *dev = data;
    
    pr_info("[内核线程] 启动\n");
    
    while (!kthread_should_stop()) {
        pr_info("[内核线程] 周期性工作\n");
        
        /* 可以睡眠 */
        msleep_interruptible(2000);
        
        /* 检查是否应该停止 */
        if (kthread_should_stop())
            break;
    }
    
    pr_info("[内核线程] 退出\n");
    complete(&dev->thread_done);
    
    return 0;
}

/* ============ 设备探测/移除 ============ */

static int async_demo_probe(struct platform_device *pdev)
{
    struct async_demo_dev *dev;
    int ret;
    
    pr_info("async_demo: 设备探测\n");
    
    dev = devm_kzalloc(&pdev->dev, sizeof(*dev), GFP_KERNEL);
    if (!dev)
        return -ENOMEM;
    
    demo_dev = dev;
    dev->pdev = pdev;
    platform_set_drvdata(pdev, dev);
    
    /* 初始化自旋锁 */
    spin_lock_init(&dev->lock);
    atomic_set(&dev->running, 1);
    
    /* 初始化工作队列 */
    INIT_WORK(&dev->work, demo_work_handler);
    INIT_DELAYED_WORK(&dev->delayed_work, demo_delayed_work_handler);
    
    /* 初始化Tasklet */
    tasklet_init(&dev->tasklet, demo_tasklet_handler, (unsigned long)dev);
    
    /* 初始化定时器 */
    timer_setup(&dev->timer, demo_timer_callback, 0);
    
    /* 初始化高精度定时器 */
    hrtimer_init(&dev->hrtimer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
    dev->hrtimer.function = demo_hrtimer_callback;
    
    /* 初始化完成量 */
    init_completion(&dev->thread_done);
    
    /* 注册中断（示例，实际设备需要真实IRQ）*/
    /*
    ret = request_threaded_irq(dev->irq, demo_irq_handler, 
                               demo_irq_thread_handler,
                               IRQF_SHARED, DRIVER_NAME, dev);
    if (ret) {
        dev_err(&pdev->dev, "无法注册中断\n");
        return ret;
    }
    */
    
    /* 创建内核线程 */
    dev->kthread = kthread_run(demo_kthread_func, dev, "async_demo_thread");
    if (IS_ERR(dev->kthread)) {
        ret = PTR_ERR(dev->kthread);
        goto err_irq;
    }
    
    /* 启动定时器 */
    mod_timer(&dev->timer, jiffies + msecs_to_jiffies(500));
    
    /* 启动高精度定时器 */
    hrtimer_start(&dev->hrtimer, ms_to_ktime(100), HRTIMER_MODE_REL);
    
    /* 启动延迟工作 */
    schedule_delayed_work(&dev->delayed_work, msecs_to_jiffies(1000));
    
    pr_info("async_demo: 所有异步机制已初始化\n");
    
    return 0;

err_irq:
    /* free_irq(dev->irq, dev); */
    return ret;
}

static int async_demo_remove(struct platform_device *pdev)
{
    struct async_demo_dev *dev = platform_get_drvdata(pdev);
    
    pr_info("async_demo: 设备移除\n");
    
    /* 停止运行 */
    atomic_set(&dev->running, 0);
    
    /* 停止内核线程 */
    if (dev->kthread) {
        kthread_stop(dev->kthread);
        wait_for_completion(&dev->thread_done);
    }
    
    /* 停止高精度定时器 */
    hrtimer_cancel(&dev->hrtimer);
    
    /* 停止普通定时器 */
    del_timer_sync(&dev->timer);
    
    /* 停止tasklet */
    tasklet_kill(&dev->tasklet);
    
    /* 取消工作队列 */
    cancel_work_sync(&dev->work);
    cancel_delayed_work_sync(&dev->delayed_work);
    
    /* 释放中断 */
    /* free_irq(dev->irq, dev); */
    
    pr_info("async_demo: 清理完成\n");
    
    return 0;
}

/* 平台驱动结构 */
static struct platform_driver async_demo_driver = {
    .probe = async_demo_probe,
    .remove = async_demo_remove,
    .driver = {
        .name = DRIVER_NAME,
    },
};

/* 模块初始化 */
static int __init async_demo_init(void)
{
    pr_info("async_demo: 模块加载\n");
    return platform_driver_register(&async_demo_driver);
}

/* 模块退出 */
static void __exit async_demo_exit(void)
{
    platform_driver_unregister(&async_demo_driver);
    pr_info("async_demo: 模块卸载\n");
}

module_init(async_demo_init);
module_exit(async_demo_exit);

MODULE_AUTHOR("Demo");
MODULE_DESCRIPTION("Linux Async Mechanisms Demo Driver");
MODULE_LICENSE("GPL");

