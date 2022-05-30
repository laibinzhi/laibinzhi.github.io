---
title: Android异步消息处理机制完全解析
date: 2022-05-30 11:39:30
tags:
  - Android
  - FrameWork
  - 
---


# Android异步消息处理机制完全解析

## Handle

### Handle的使用

- Handler.sendMessage

<!--more-->


  ```- java
  /** 
    * 方式1：新建Handler子类（内部类）
    */
  
      // 步骤1：自定义Handler子类（继承Handler类） & 复写handleMessage（）方法
      class mHandler extends Handler {
  
          // 通过复写handlerMessage() 从而确定更新UI的操作
          @Override
          public void handleMessage(Message msg) {
           ...// 需执行的UI操作
              
          }
      }
  
      // 步骤2：在主线程中创建Handler实例
          private Handler mhandler = new mHandler();
  
      // 步骤3：创建所需的消息对象
          Message msg = Message.obtain(); // 实例化消息对象
          msg.what = 1; // 消息标识
          msg.obj = "AA"; // 消息内容存放
  
      // 步骤4：在工作线程中 通过Handler发送消息到消息队列中
      // 可通过sendMessage（） / post（）
      // 多线程可采用AsyncTask、继承Thread类、实现Runnable
          mHandler.sendMessage(msg);
  
      // 步骤5：开启工作线程（同时启动了Handler）
      // 多线程可采用AsyncTask、继承Thread类、实现Runnable
  
  
  /** 
    * 方式2：匿名内部类
    */
     // 步骤1：在主线程中 通过匿名内部类 创建Handler类对象
              private Handler mhandler = new  Handler(){
                  // 通过复写handlerMessage()从而确定更新UI的操作
                  @Override
                  public void handleMessage(Message msg) {
                          ...// 需执行的UI操作
                      }
              };
  
    // 步骤2：创建消息对象
      Message msg = Message.obtain(); // 实例化消息对象
    msg.what = 1; // 消息标识
    msg.obj = "AA"; // 消息内容存放
    
    // 步骤3：在工作线程中 通过Handler发送消息到消息队列中
    // 多线程可采用AsyncTask、继承Thread类、实现Runnable
     mHandler.sendMessage(msg);
  
    // 步骤4：开启工作线程（同时启动了Handler）
    // 多线程可采用AsyncTask、继承Thread类、实现Runnable
  
  
  ```

- Handler.post（）

```java
// 步骤1：在主线程中创建Handler实例
    private Handler mhandler = new mHandler();

    // 步骤2：在工作线程中 发送消息到消息队列中 & 指定操作UI内容
    // 需传入1个Runnable对象
    mHandler.post(new Runnable() {
            @Override
            public void run() {
                ... // 需执行的UI操作 
            }

    });

    // 步骤3：开启工作线程（同时启动了Handler）
    // 多线程可采用AsyncTask、继承Thread类、实现Runnable

```



### 源码解析

#### Handle和Looper

先看下在我们实例化Handler的时候，Handler的构造方法中都做了什么

```java
    public Handler(@Nullable Callback callback, boolean async) {
        mLooper = Looper.myLooper();
        if (mLooper == null) {
            throw new RuntimeException(
                "Can't create handler inside thread " + Thread.currentThread()
                        + " that has not called Looper.prepare()");
        }
        mQueue = mLooper.mQueue;
        mCallback = callback;
        mAsynchronous = async;
    }

```

从上面，我们可以知道，在调用Looper.myLooper()之前必须要先调用Looper.prepare（）方法，现在来看下prepare方法中的内容，如下

```java
 public static void prepare() {
        prepare(true);
    }

    private static void prepare(boolean quitAllowed) {
        if (sThreadLocal.get() != null) {
            throw new RuntimeException("Only one Looper may be created per thread");
        }
        sThreadLocal.set(new Looper(quitAllowed));
    }
```

可以看到，prepare()方法调用了prepare(boolean quitAllowed)方法，prepare(boolean quitAllowed) 方法中则是实例化了一个Looper，然后将Looper设置进sThreadLocal中，到了这里就有必要了解一下ThreadLocalle。可以参考之前[Java并发编程总结](https://juejin.cn/post/7094190470720552997#heading-35)中的ThreadLocal。所以Looper.prepare方法就是将Looper与当前线程进行绑定`（当前线程就是调用Looper.prepare方法的线程）`。

> **ThreadLocal**，线程本地变量，也有些地方叫做线程本地存储，其实意思差不多。ThreadLocal可以让每个线程拥有一个属于自己的变量的副本，不会和其他线程的变量副本冲突，实现了线程的数据隔离。



在调用Looper.myLooper方法之前必须必须已经调用了Looper.prepare方法，即在实例化Handler之前就要调用Looper.prepare方法，但是我们平常在主线程中使用Handler的时候并没有调用Looper.prepare方法呀！这是为什么呢？



其实，在主线程中Android系统已经帮我们调用了Looper.prepare方法，可以看下ActivityThread类中的main方法，代码如下



```java
 public static void main(String[] args) {
        ...
        Looper.prepareMainLooper();

        ActivityThread thread = new ActivityThread();
        thread.attach(false);

        if (sMainThreadHandler == null) {
            sMainThreadHandler = thread.getHandler();
        }

        if (false) {
            Looper.myLooper().setMessageLogging(new
                    LogPrinter(Log.DEBUG, "ActivityThread"));
        }

        // End of event ActivityThreadMain.
        Trace.traceEnd(Trace.TRACE_TAG_ACTIVITY_MANAGER);
        Looper.loop();

        throw new RuntimeException("Main thread loop unexpectedly exited");
    }

```

这句话的实质就是调用了Looper的prepare方法，代码如下

```java
    @Deprecated
    public static void prepareMainLooper() {
        prepare(false);
        synchronized (Looper.class) {
            if (sMainLooper != null) {
                throw new IllegalStateException("The main Looper has already been prepared.");
            }
            sMainLooper = myLooper();
        }
    }
```



我们再看一下Handle的构造函数初始化变量中

```
mQueue = mLooper.mQueue; 
```

这句代码。这句代码就是拿到Looper中的mQueue这个成员变量，然后再赋值给Handler中的mQueue，下面看下Looper中的代码

```java
 final MessageQueue mQueue;
	private Looper(boolean quitAllowed) {
        mQueue = new MessageQueue(quitAllowed);
        mThread = Thread.currentThread();
    }

```

同过上面的代码，我们可以知道mQueue就是MessageQueue，在我们调用Looper.prepare方法时就将mQueue实例化了。消息队列是一个存放消息的容器，先进先出FIFO的数据结构。这个消息队列我们后续再说。



#### 发送消息

既然创建了一个Handle对象，那我们怎么发送消息呢？

首先需要创建一个Message对象。

常见创建Message有三种方式

1. **Message msg = new Message();**

   > 每次需要Message对象的时候都创建一个新的对象，每次都要去堆内存开辟对象存储空间 
   >

2. **Message msg =Message.obtain();**

   > obtainMessage能避免重复Message创建对象。它先判断消息池是不是为空，如果非空的话就从消息池表头的Message取走,再把表头指向 next。如果消息池为空的话说明还没有Message被放进去，那么就new出来一个Message对象。消息池使用 Message 链表结构实现，消息池默认最大值 50。消息在loop中被handler分发消费之后会执行回收的操作，将该消息内部数据清空并添加到消息链表的表头。

   - **享元模式**

3. **Message msg = handler.obtainMessage();**

   > 其内部也是调用的obtain()方法



```java
  public final boolean sendMessage(@NonNull Message msg) {
        return sendMessageDelayed(msg, 0);
    }

   public final boolean sendEmptyMessage(int what)
    {
        return sendEmptyMessageDelayed(what, 0);
    }

    public final boolean sendEmptyMessageDelayed(int what, long delayMillis) {
        Message msg = Message.obtain();
        msg.what = what;
        return sendMessageDelayed(msg, delayMillis);
    }


    public final boolean sendEmptyMessageAtTime(int what, long uptimeMillis) {
        Message msg = Message.obtain();
        msg.what = what;
        return sendMessageAtTime(msg, uptimeMillis);
    }

    public final boolean sendMessageDelayed(@NonNull Message msg, long delayMillis) {
        if (delayMillis < 0) {
            delayMillis = 0;
        }
        return sendMessageAtTime(msg, SystemClock.uptimeMillis() + delayMillis);
    }


    public boolean sendMessageAtTime(@NonNull Message msg, long uptimeMillis) {
        MessageQueue queue = mQueue;
        if (queue == null) {
            RuntimeException e = new RuntimeException(
                    this + " sendMessageAtTime() called with no mQueue");
            Log.w("Looper", e.getMessage(), e);
            return false;
        }
        return enqueueMessage(queue, msg, uptimeMillis);
    }
```

可以看到，上面所有的消息最终都是进入sendMessageAtTime



```java
public boolean sendMessageAtTime(@NonNull Message msg, long uptimeMillis) {
  //其中 mQueue 是消息队列，从 Looper 中获取的  
  MessageQueue queue = mQueue;
    if (queue == null) {
        RuntimeException e = new RuntimeException(
                this + " sendMessageAtTime() called with no mQueue");
        Log.w("Looper", e.getMessage(), e);
        return false;
    }
  //调用 enqueueMessage 方法
    return enqueueMessage(queue, msg, uptimeMillis);
}
```



我们看一下MessageQueue enqueueMessage



```java
boolean enqueueMessage(Message msg, long when) {
  //每一个 Message 必须有一个 target
    if (msg.target == null) {
        throw new IllegalArgumentException("Message must have a target.");
    }

    synchronized (this) {
        if (msg.isInUse()) {
            throw new IllegalStateException(msg + " This message is already in use.");
        }

        if (mQuitting) {
          //正在退出时，回收 msg，加入到消息池
            IllegalStateException e = new IllegalStateException(
                    msg.target + " sending message to a Handler on a dead thread");
            Log.w(TAG, e.getMessage(), e);
            msg.recycle();
            return false;
        }

        msg.markInUse();
        msg.when = when;
        Message p = mMessages;
        boolean needWake;
      //p 为 null(代表 MessageQueue 没有消息） 或者 msg 的触发时间是队列中 最早的， 则进入该该分支
        if (p == null || when == 0 || when < p.when) {
            // New head, wake up the event queue if blocked.
            msg.next = p;
            mMessages = msg;
            needWake = mBlocked;
        } else {
 //将消息按时间顺序插入到 MessageQueue。一般地，不需要唤醒事件队列， 除非 //消息队头存在 barrier，并且同时 Message 是队列中最早的异步消息。
            needWake = mBlocked && p.target == null && msg.isAsynchronous();
            Message prev;
            for (;;) {
                prev = p;
                p = p.next;
                if (p == null || when < p.when) {
                    break;
                }
                if (needWake && p.isAsynchronous()) {
                    needWake = false;
                }
            }
            msg.next = p; // invariant: p == prev.next
            prev.next = msg;
        }

        // We can assume mPtr != 0 because mQuitting is false.
        if (needWake) {
            nativeWake(mPtr);
        }
    }
    return true;
}
```

MessageQueue 是按照 Message 触发时间的先后顺序排列的，队头的消息是将要最早触发的消息。当有消息需要加入消息队列时，会从队列头开始遍历，直到找 到消息应该插入的合适位置，以保证所有消息的时间顺序。



#### 获取消息

那怎么获取消息呢？

当发送了消息后，在 MessageQueue 维护了消息队列，然后在 Looper 中通过 loop() 方法，不断地获取消息。上面对 loop()方法进行了介绍，其中最重要的是调用 了 queue.next()方法,通过该方法来提取下一条信息。下面我们来看一下 next() 方法的具体流程。 

```java
Message next() {
    final long ptr = mPtr;
  //当消息循环已经退出，则直接返回
    if (ptr == 0) {
        return null;
    }

    int pendingIdleHandlerCount = -1; // 循环迭代的首次为-1
    int nextPollTimeoutMillis = 0;
    for (;;) {
        if (nextPollTimeoutMillis != 0) {
            Binder.flushPendingCommands();
        }

      //阻塞操作，当等待 nextPollTimeoutMillis 时长，或者消息队列被唤醒，都会返回
        nativePollOnce(ptr, nextPollTimeoutMillis);

        synchronized (this) {
            // Try to retrieve the next message.  Return if found.
            final long now = SystemClock.uptimeMillis();
            Message prevMsg = null;
            Message msg = mMessages;
            if (msg != null && msg.target == null) {
             //当消息 Handler 为空时，查询 MessageQueue 中的下一条异步消息 m sg，为空则退出循环。
                do {
                    prevMsg = msg;
                    msg = msg.next;
                } while (msg != null && !msg.isAsynchronous());
            }
            if (msg != null) {
                if (now < msg.when) {
                   //当异步消息触发时间大于当前时间，则设置下一次轮询的超时时长
                    nextPollTimeoutMillis = (int) Math.min(msg.when - now, Integer.MAX_VALUE);
                } else {
                    // 获取一条消息，并返回
                    mBlocked = false;
                    if (prevMsg != null) {
                        prevMsg.next = msg.next;
                    } else {
                        mMessages = msg.next;
                    }
                    msg.next = null;
                    if (DEBUG) Log.v(TAG, "Returning message: " + msg);
                  //设置消息的使用状态，即 flags |= FLAG_IN_USE
                    msg.markInUse();
                    return msg;
                }
            } else {
                // 没有更多消息
                nextPollTimeoutMillis = -1;
            }

            //消息正在退出，返回null
            if (mQuitting) {
                dispose();
                return null;
            }
......
           
    }
}
```

nativePollOnce 是阻塞操作，其中 nextPollTimeoutMillis 代表下一个消息到来前， 还需要等待的时长；当 nextPollTimeoutMillis = -1 时，表示消息队列中无消息， 会一直等待下去。 可以看出 next()方法根据消息的触发时间，获取下一条需要执行的消息,队列中 消息为空时，则会进行阻塞操作。 



#### 分发消息

在 loop()方法中，获取到下一条消息后，执行 msg.target.dispatchMessage(msg)， 来分发消息到目标 Handler 对象。 下面就来具体看下 dispatchMessage(msg)方法的执行流程。



```java
public void dispatchMessage(@NonNull Message msg) {
    if (msg.callback != null) {
      //当 Message 存在回调方法，回调 msg.callback.run()方法；
        handleCallback(msg);
    } else {
        if (mCallback != null) {
          //当 Handler 存在 Callback 成员变量时，回调方法 handleMessage()；
            if (mCallback.handleMessage(msg)) {
                return;
            }
        }
      //Handler 自身的回调方法 handleMessage()
        handleMessage(msg);
    }
}
```

**分发消息流程：** 

当 Message 的 msg.callback 不为空时，则回调方法 msg.callback.run(); 

当 Handler 的 mCallback 不为空时，则回调方法 mCallback.handleMessage(msg)； 

最后调用 Handler 自身的回调方法 handleMessage()，该方法默认为空，Handler 

子类通过覆写该方法来完成具体的逻辑。 

**消息分发的优先级：** 

Message 的回调方法：message.callback.run()，优先级最高；



### Handle总结

![WechatIMG167](https://s2.loli.net/2022/05/29/iIv9V8xqAmhCZXD.jpg)

在使用Handle之前必须调用Looper.prepare，这句代码的工作就是将Looper和当前线程进行绑定。在实例化Handle的时候，通过Looper.myLooper方法获取Looper，然后再获得Looper中的MessageQueue。子线程调用Handle的sendMessage或者是post Runable都是将Message放进MessageQueue中，然后调用Looper.loop方法来从MessageQueue取出Message，在取到Message的时候，执行msg.target.dispatchMessage方法，这个方法内部就是handle的handleMessage方法。



> 从四个方面看Handler、Message、MessageQueue 和 Looper
>
> - Handler:负责消息的发送和处理
>
> - Message:消息对象，类似于链表的一个结点;
>
> - MessageQueue:消息队列，用于存放消息对象的数据结构;
> - Looper:消息队列的处理者（用于轮询消息队列的消息对象)
>
> Handler发送消息时调用MessageQueue的enqueueMessage插入一条信息到MessageQueue,Looper不断轮询调用MeaasgaQueue的next方法 如果发现message就调用handler的dispatchMessage，dispatchMessage被成功调用，接着调用handlerMessage()。



### Handler postDelayed的原理

1. 消息是通过MessageQueen中的enqueueMessage()方法加入消息队列中的，并且它在放入中就进行好排序，链表头的延迟时间小，尾部延迟时间最大
2. Looper.loop()通过MessageQueue中的next()去取消息
3. next()中如果当前链表头部消息是延迟消息，则根据延迟时间进行消息队列会阻塞，不返回给Looper message，知道时间到了，返回给message
4. 如果在阻塞中有新的消息插入到链表头部则唤醒线程
5. Looper将新消息交给回调给handler中的handleMessage后，继续调用MessageQueen的next()方法，如果刚刚的延迟消息还是时间未到，则计算时间继续阻塞

**handler.postDelay() 的实现 是通过MessageQueue中执行时间顺序排列，消息队列阻塞，和唤醒的方式结合实现的。**



### 线程同步

**怎么保证线程同步问题**？

Handler机制里面最主要的类MessageQueue，这个类就是所有消息的存储仓库，在这个仓库中，我们如何的管理好消息，这个就是一个关键点了。消息管理就2点：1）消息入库（enqueueMessage），2）消息出库（next），所以这两个接口是确保线程安全的主要档口。



首先我们看一下enqueueMessage源码和next源码，都加了synchronized内置锁。说明的是对所有调用同一个MessageQueue对象的线程来说，他们都是互斥的，然而，在我们的Handler里

面，一个线程是对应着一个唯一的Looper对象，而Looper中又只有一个唯一的MessageQueue。所以，我们主线程就只有一个MessageQueue对象，也就是说，所有的子线程向主线程发送消息的时候，主线程一次都只会处理一个消息，其他的都需要等待，那么这个时候消息队列就不会出现混乱。

而next函数可能会有疑问：我从线程里面取消息，而且每次都是队列的头部取，那么它加锁是不是没有意义呢？答案是否定的，我们必须要在next里面加锁，因为，这样由于synchronized（this）作用范围是所有 this正在访问的代码块都会有保护作用，也就是它可以保证 next函数和 enqueueMessage函数能够实现互斥。这样才能真正的保证多线程访问的时候messagequeue的有序进行。

### 同步屏障

#### 定义

屏障的意思即为阻碍，顾名思义，**同步屏障就是阻碍同步消息，只让异步消息通过**。如何开启同步屏障呢？

```java
MessageQueue#postSyncBarrier()
```

#### 源码解析

```java
@UnsupportedAppUsage
@TestApi
public int postSyncBarrier() {
    return postSyncBarrier(SystemClock.uptimeMillis());
}
```

```java
private int postSyncBarrier(long when) {
    synchronized (this) {
        final int token = mNextBarrierToken++;
       //从消息池中获取Message
        final Message msg = Message.obtain();
        msg.markInUse();
      //初始化Message对象的时候，并没有给target赋值，因此 target==null
        msg.when = when;
        msg.arg1 = token;

        Message prev = null;
        Message p = mMessages;
        if (when != 0) {
          //如果开启同步屏障的时间（假设记为T）T不为0，且当前的同步消息里有时间小于T，则prev也不为null
            while (p != null && p.when <= when) {
                prev = p;
                p = p.next;
            }
        }
      //根据prev是不是为null，将 msg 按照时间顺序插入到 消息队列（链表）的合适位置
        if (prev != null) { // invariant: p == prev.next
            msg.next = p;
            prev.next = msg;
        } else {
            msg.next = p;
            mMessages = msg;
        }
        return token;
    }
}
```



可以看到，Message 对象初始化的时候并没有给 target 赋值，因此， **target == null** 的 来源就找到了。上面消息的插入也做了相应的注释。这样，一条 target == null 的消息就进入了消息队列。那么，开启同步屏障后，所谓的异步消息又是如何被处理的呢？



如果对消息机制有所了解的话，应该知道消息的最终处理是在消息轮询器 Looper#loop() 中，而 loop() 循环中会调用 MessageQueue#next() 从消息队列中进行取消息。



```java
Message next() {
// 1.如果nextPollTimeoutMillis=-1，一直阻塞不会超时。 
 // 2.如果nextPollTimeoutMillis=0，不会阻塞，立即返回。
  // 3.如果nextPollTimeoutMillis>0，最长阻塞nextPollTimeoutMillis毫秒(超时)
  // 如果期间有程序唤醒会立即返回。
    int pendingIdleHandlerCount = -1; // -1 only during first iteration
    int nextPollTimeoutMillis = 0;
  //next()也是一个无限循环
    for (;;) {
        if (nextPollTimeoutMillis != 0) {
            Binder.flushPendingCommands();
        }

        nativePollOnce(ptr, nextPollTimeoutMillis);

        synchronized (this) {
           //获取系统开机到现在的时间
            final long now = SystemClock.uptimeMillis();
            Message prevMsg = null;
            Message msg = mMessages; //当前链表的头结点
            if (msg != null && msg.target == null) {
                // 如果target==null，那么它就是屏障，需要循环遍历，一直往后找到第一个异步的消息
                do {
                    prevMsg = msg;
                    msg = msg.next;
                } while (msg != null && !msg.isAsynchronous());
            }
            if (msg != null) {
              //如果有消息需要处理，先判断时间有没有到，如果没到的话设置一下阻塞时间， 
              //场景如常用的postDelay
                if (now < msg.when) {
                  //计算出离执行时间还有多久赋值给nextPollTimeoutMillis，
                  //表示nativePollOnce方法要等待nextPollTimeoutMillis时长后返回
                    nextPollTimeoutMillis = (int) Math.min(msg.when - now, Integer.MAX_VALUE);
                } else {
                   // 获取到消息
                    mBlocked = false;
                  //链表操作，获取msg并且删除该节点
                    if (prevMsg != null) {
                        prevMsg.next = msg.next;
                    } else {
                        mMessages = msg.next;
                    }
                    msg.next = null;
                    if (DEBUG) Log.v(TAG, "Returning message: " + msg);
                    msg.markInUse();
                  //返回拿到的消息
                    return msg;
                }
            } else {
                //没有消息，nextPollTimeoutMillis复位
                nextPollTimeoutMillis = -1;
            }

          ...
    }
}
```



从上面可以看出，当消息队列开启同步屏障的时候（即标识为 msg.target == null ），消息机制在处理消息的时候，优先处理异步消息。这样，同步屏障就起到了一种过滤和优先级的作用。

- 那么这些同步消息什么时候可以被处理呢？那就需要先移除这个同步屏障，即调用 **removeSyncBarrier**() 。



#### 同步屏障应用场景

Android 系统中的 UI 更新相关的消息即为异步消息，需要优先处理。

比如，在 View 更新时，draw、requestLayout、invalidate 等很多地方都调用了

**ViewRootImpl#scheduleTraversals()** ，如下：

```java
void scheduleTraversals() {
    if (!mTraversalScheduled) {
        mTraversalScheduled = true;
      //开启同步屏障
        mTraversalBarrier = mHandler.getLooper().getQueue().postSyncBarrier();
      //发送异步消息  
      mChoreographer.postCallback(
                Choreographer.CALLBACK_TRAVERSAL, mTraversalRunnable, null);
        notifyRendererOfFramePending();
        pokeDrawLockIfNeeded();
    }
}
```

postCallback() 最终走到了 **ChoreographerpostCallbackDelayedInternal**() ：



```java
private void postCallbackDelayedInternal(int callbackType,
        Object action, Object token, long delayMillis) {
    if (DEBUG_FRAMES) {
        Log.d(TAG, "PostCallback: type=" + callbackType
                + ", action=" + action + ", token=" + token
                + ", delayMillis=" + delayMillis);
    }

    synchronized (mLock) {
        final long now = SystemClock.uptimeMillis();
        final long dueTime = now + delayMillis;
        mCallbackQueues[callbackType].addCallbackLocked(dueTime, action, token);

        if (dueTime <= now) {
            scheduleFrameLocked(now);
        } else {
            Message msg = mHandler.obtainMessage(MSG_DO_SCHEDULE_CALLBACK, action);
            msg.arg1 = callbackType;
            msg.setAsynchronous(true);//开启异步消息
            mHandler.sendMessageAtTime(msg, dueTime);
        }
    }
}
```

这里就开启了同步屏障，并发送异步消息，由于 UI 更新相关的消息是优先级最高的，这样系统就会优先处理这些异步消息。

最后，当要移除同步屏障的时候需要调用 ViewRootImpl#unscheduleTraversals() 。

```java
void unscheduleTraversals() {
    if (mTraversalScheduled) {
        mTraversalScheduled = false;
      //移除同步屏障
        mHandler.getLooper().getQueue().removeSyncBarrier(mTraversalBarrier);
        mChoreographer.removeCallbacks(
                Choreographer.CALLBACK_TRAVERSAL, mTraversalRunnable, null);
    }
}
```



#### 同步屏障总结

同步屏障的设置可以方便地处理那些优先级较高的异步消息。当我们调用Handler.getLooper().getQueue().postSyncBarrier() 并设置消息的 setAsynchronous(true) 时，target 即 为 null ，也就开启了同步屏障。当在消息轮询器 Looper 在 loop() 中循环处理消息时，如若开启了同步屏障，会优先处理其中的异步消息，而阻碍同步消息。





### 常见问题

#### 1. **子线程中能不能直接**new一个Handler,为什么主线程可以？

主线程的Looper第一次调用loop方法,什么时候,哪个类不能，因为Handler 的构造方法中，会通过Looper.myLooper()获取looper对象，如果为空，则抛出异常，主线程则因为已在入口处ActivityThread的main方法中通过 Looper.prepareMainLooper()获取到这个对象，并通过 Looper.loop()开启循环，在子线程中若要使用handler，可先通过Loop.prepare获取到looper对象，并使用Looper.loop()开启循环

#### 2. **Handler**导致的内存泄露原因及其解决方案

**原因**:

1. Java中非静态内部类和匿名内部类都会隐式持有当前类的外部引用
1. 我们在Activity中使用非静态内部类初始化了一个Handler,此Handler就会持有当前Activity的引用。
1. 我们想要一个对象被回收，那么前提它不被任何其它对象持有引用，所以当我们Activity页面关闭之后,存在引用关系："未被处理 / 正处理的消息 -> Handler实例 -> 外部类",如果在Handler消息队列 还有未处理的消息 / 正在处理消息时 导致Activity不会被回收，从而造成内存泄漏 

**解决方案**: 

1. 将Handler的子类设置成 静态内部类,使用WeakReference弱引用持有Activity实例 
1. 当外部类结束生命周期时，清空Handler内消息队列



#### 3. **Handler**的post与sendMessage的区别和应用场景

1. 源码

   - sendMessage

     > sendMessage-sendMessageAtTime-enqueueMessage。

   - post

     > sendMessage-getPostMessage-sendMessageAtTime-enqueueMessage getPostMessage会先生成一个Messgae，并且把runnable赋值给message的callback

2. Looper->dispatchMessage处理时

   ```java
   public void dispatchMessage(@NonNull Message msg) {
       if (msg.callback != null) {
           handleCallback(msg);
       } else {
           if (mCallback != null) {
               if (mCallback.handleMessage(msg)) {
                   return;
               }
           }
           handleMessage(msg);
       }
   }
   ```

   dispatchMessage方法中直接执行post中的runnable方法。

   而sendMessage中如果mCallback不为null就会调用mCallback.handleMessage(msg)方法，如果handler内的callback不为空，执行mCallback.handleMessage(msg)这个处理消息并判断返回是否为true，如果返回true，消息处理结束，如果返回false,handleMessage(msg)处理。否则会直接调用handleMessage方法。

3. 总结

   > post方法和handleMessage方法的不同在于，区别就是调用post方法的消息是在post传递的Runnable对象的run方法中处理，而调用sendMessage方法需要重写handleMessage方法或者给handler设置callback，在callback的handleMessage中处理并返回true

#### 4. **Android**中为什么主线程不会因为Looper.loop()里的死循环卡死？

**MessageQueue#next 在没有消息的时候会阻塞，如何恢复？**

他不阻塞的原因是**epoll**机制，他是linux里面的，在native层会有一个读取端和一个写入端，当有消息发送过来的时候会去唤醒读取端，然后进行消息发送与处理，没消息的时候是处于休眠状态，所以他不会阻塞他。



#### 5. ANR和Handle的联系？

Handler是线程间通讯的机制，Android中，网络访问、文件处理等耗时操作必须放到子线程中去执行，否则将会造成ANR异常。 ANR异常：Application Not Response 应用程序无响应 产生ANR异常的原因：在主线程执行了耗时操作，对Activity来说，主线程阻塞5秒将造成ANR异常，对BroadcastReceiver来说，主线程阻塞10秒将会造成ANR异常。 解决ANR异常的方法：耗时操作都在子线程中去执行 但是，Android不允许在子线程去修改UI，可我们又有在子线程去修改UI的需求，因此需要借助Handler。





#### 6. 子线程中维护的Looper，消息队列无消息的时候的处理方案是什么？有什么用？

子线程中维护的looper在无消息时调用**quit**,可以结束循环.loop()是一个死循环,想要退出,必须msg == null

```java
public static void loop() {
        for (;;) {
            Message msg = queue.next(); // might block
            if (msg == null) {
                // No message indicates that the message queue is quitting.
                return;
            }
            msg.recycleUnchecked();
        }
    }

```



**MessageQueue中的quit如下**

```java
void quit(boolean safe) {
    if (!mQuitAllowed) {
        throw new IllegalStateException("Main thread not allowed to quit.");
    }

    synchronized (this) {
        if (mQuitting) {
            return;
        }
        mQuitting = true;

        if (safe) {
            removeAllFutureMessagesLocked();
        } else {
            removeAllMessagesLocked();
        }

        // We can assume mPtr != 0 because mQuitting was previously false.
        nativeWake(mPtr);
    }
}
```



1. prepare()
2. loop()

3. quit()



#### 6.Looper** **如何与** **Thread** 关联的

Looper 与 Thread 之间是通过 ThreadLocal 关联的，这个可以看 Looper#prepare() 方法 Looper 中有一个ThreadLocal 类型的 sThreadLocal静态字段，Looper通过它的 get 和 set 方法来赋值和取值。 由于 ThreadLocal是与线程绑定的，所以我们只要把 Looper 与 ThreadLocal 绑定了，那 Looper 和 Thread 也就关联上了





#### 7. Looper的quit和quitSafely有什么区别

```java
public void quitSafely() {
    mQueue.quit(true);
}
```



```java
void quit(boolean safe) {
        if (!mQuitAllowed) {
            throw new IllegalStateException("Main thread not allowed to quit.");
        }

        synchronized (this) {
            if (mQuitting) {
                return;
            }
            mQuitting = true;

            if (safe) {
                removeAllFutureMessagesLocked();
            } else {
                removeAllMessagesLocked();
            }

            // We can assume mPtr != 0 because mQuitting was previously false.
            nativeWake(mPtr);
        }
}
```

- 当我们调用Looper的quit方法时，实际上运行了MessageQueue中的removeAllMessagesLocked方法。该方法的作用是把MessageQueue消息池中全部的消息全部清空，不管是延迟消息（延迟消息是指通过sendMessageDelayed或通过postDelayed等方法发送的须要延迟运行的消息）还是非延迟消息。

- 当我们调用Looper的quitSafely方法时，实际上运行了MessageQueue中的removeAllFutureMessagesLocked方法，通过名字就能够看出。该方法仅仅会清空MessageQueue消息池中全部的延迟消息。并将消息池中全部的非延迟消息派发出去让Handler去处理，**quitSafely相比于quit方法安全之处在于清空消息之前会派发全部的非延迟消息。**

- 不管是调用了quit方法还是quitSafely方法仅仅会，Looper就不再接收新的消息。即在调用了Looper的quit或quitSafely方法之后，消息循环就终结了。这时候再通过Handler调用sendMessage或post等方法发送消息时均返回false，表示消息没有成功放入消息队列MessageQueue中，由于消息队列已经退出了。





#### 8. MessageQueue没有消息时候会怎样？阻塞之后怎么唤醒呢？说说pipe/epoll机制？



## IdeaHandle

参考https://juejin.cn/post/6844904068129751047#heading-3

**常见问题**

1. IdleHandler 有什么用？

   > 1. IdleHandler 是 Handler 提供的一种在消息队列空闲时，执行任务的时机；
   > 2. 当 MessageQueue 当前没有立即需要处理的消息时，会执行 IdleHandler；

2. MessageQueue 提供了 add/remove IdleHandler 的方法，是否需要成对使用？

   > 1. 不是必须；
   > 2. IdleHandler.queueIdle() 的返回值，可以移除加入 MessageQueue 的 IdleHandler

3. 当 mIdleHanders 一直不为空时，为什么不会进入死循环？

   > 1. 只有在 pendingIdleHandlerCount 为 -1 时，才会尝试执行 mIdleHander；
   > 2. pendingIdlehanderCount 在 next() 中初始时为 -1，执行一遍后被置为 0，所以不会重复执行；

4. 是否可以将一些不重要的启动服务，搬移到 IdleHandler 中去处理？

   > 1. 不建议；
   > 2. IdleHandler 的处理时机不可控，如果 MessageQueue 一直有待处理的消息，那么 IdleHander 的执行时机会很靠后；

5. IdleHandler 的 queueIdle() 运行在那个线程？

   > 1. 陷进问题，queueIdle() 运行的线程，只和当前 MessageQueue 的 Looper 所在的线程有关；
   > 2. 子线程一样可以构造 Looper，并添加 IdleHandler；





## HandleThread

### 背景

**HandlerThread**是Thread的子类，严格意义上来说就是一个线程，只是它在自己的线程里面帮我们创建了Looper。

1. **方便使用**：

   a.  方便初始化

   b. 方便获取线程looper

2. **保证了线程安全**

   我们一般在Thread里面 线程Looper进行初始化的代码里面，必须要对Looper.prepare(),同时要调用Loop。

   ```java
   @Override public void run() {
       Looper.prepare(); 
       Looper.loop();
   }
   ```

   而我们要使用子线程中的Looper的方式是怎样的呢？看下面的代码

   ```java
   Thread thread = new Thread(new Runnable() {
       Looper looper; 
       @Override public void run() { 
             Looper.prepare(); 
             looper =Looper.myLooper();
             Looper.loop(); 
       }
        public Looper getLooper() { 
          return looper; 
        } 
   }); 
   thread.start(); 
   Handler handler = new Handler(thread.getLooper());
   ```

   上面这段代码存在以下问题：

   1. 在初始化子线程的handler的时候，我们无法将子线程的looper传值给Handler,解决办法有如下办法：

      - 可以将Handler的初始化放到 Thread里面进行
      - 可以创建一个独立的类继承Thread，然后，通过类的对象获取。

      这两种办法都可以，但是，这个工作 HandlerThread帮我们完成了

   2. 依据多线程的工作原理，我们在上面的代码中，调用 thread.getLooper（）的时候，此时的looper可能还没有初始化，此时是不是可能会挂掉呢



### 特点

- HandleThread本质上本质线程类，继承Thread

- 内部有looper对象，run方法中开启了loop循环
- 通过获取looper对象传递给Handler对象，可以在handleMessage中执行异步任务；
- 优点是不会有堵塞，减少了性能的消耗，缺点是不能同时执行多任务的处理，需要进行等待处理，处理的效率比较低；
- 和线程池并发不同，它是串行队列，它背后只有一个线程；它的run方法是一个无限循环，明确不需要使用时，需要调用quit或quitSafely退出；





## IntentService

### 定义

- 是执行并处理异步请求的一个特殊的service,由于它是一个Service，它的优先级比普通的后台线程要高，不易被系统杀死，它适合执行一些优先级较高的后台任务。

- 内部封装了handlerthread和handler，利用handlerThread处理耗时操作，启动方式和传统的service启动方式一样，同时，任务执行完毕后，它会自动的停止，不需要我们手动调用stopserivice方法。

- 它可以启动多次，每一个耗时的操作都会以工作队列的方式在IntentService得onHandleIntent回掉方法中执行，并且，每次只会执行一个工作线程，执行完毕后才会执行第二个。它是串行的。

### 使用方法

自定义一个类继承IntentService,实现onHandlerIntent()方法，该方法是在子线程中执行，所以可以进行一些耗时的操作；


```java
class MyIntentService extends IntentService{

    public MyIntentService(String name) {
        super(name);
    }
    /**
     * 工作线程中执行
     */
    @Override
    protected void onHandleIntent(@Nullable Intent intent) {
        String task_action = intent.getStringExtra("task_action");
        SystemClock.sleep(3000);//模拟耗时任务
        Log.d("MyIntentService", "handle task:" + task_action);
    }
}
```

启动方式和传统一样：

```java
Intent service=new Intent(this,MyIntentService.class);
service.putExtra("task_action","task1");
startService(service);

service.putExtra("task_action","task2");
startActivity(service);
```

### 源码分析

封装了HandlerThread和Hanler的异步框架；

handler发送消息，处理消息时回掉**onHandleIntent**（）方法；创建hanlder需要提供looper,looper来源于HandlerThread,在HandlerThread这个子线程构建了一个消息循环系统，handler处理消息的线程就是创建handler的线程，即handlerThread这个线程；

