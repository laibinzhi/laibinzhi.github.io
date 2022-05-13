---
title: RxJava源码解析
date: 2022-05-13 10:03:02
tags:
  - Android
  - Java
  - RxJava
  - 源码
---

# RxJava源码解析

## 一，简单使用

```java
   Observable observable = Observable.create(new ObservableOnSubscribe<String>() {
            @Override
            public void subscribe(@NonNull ObservableEmitter<String> emitter) throws Throwable {
                emitter.onNext("hello");
            }
        });
        Observer<String> observer = new Observer<String>() {
            @Override
            public void onSubscribe(@NonNull Disposable d) {
                Log.d(TAG, "onSubscribe() called with: d = [" + d + "]");
            }

            @Override
            public void onNext(@NonNull String s) {
                Log.d(TAG, "onNext() called with: s = [" + s + "]");
            }

            @Override
            public void onError(@NonNull Throwable e) {
                Log.d(TAG, "onError() called with: e = [" + e + "]");
            }

            @Override
            public void onComplete() {
                Log.d(TAG, "onComplete() called");
            }
        };
        observable.subscribe(observer);
```

**目标：**

- 被观察者 Observable 如何生产事件的？

- 被观察者 Observable 何时生产事件的？

- 观察者 Observer 是何时接收到上游事件的？

- Observable 与 Observer 是如何关联在一起的？


<!--more-->


### **Observable**

**Observable 是数据的上游，即事件生产者**

首先我们来了解一下事件是如何生成的，我们看一下 *Observable.create()*方法。

```java
   @CheckReturnValue
    @NonNull
    @SchedulerSupport(SchedulerSupport.NONE)
    public static <T> Observable<T> create(@NonNull ObservableOnSubscribe<T> source) {
        // ObservableOnSubscribe 是个接口，只包含 subscribe 方法，是事件生产的源头
        Objects.requireNonNull(source, "source is null");// 判空
        return RxJavaPlugins.onAssembly(new ObservableCreate<>(source));
    }
```

最重要的是 **RxJavaPlugins.onAssembly(new ObservableCreate<T>(source));**这句代码。

继续跟踪进去

```java
 @NonNull
    public static <T> Observable<T> onAssembly(@NonNull Observable<T> source) {
        Function<? super Observable, ? extends Observable> f = onObservableAssembly;
        if (f != null) {
            return apply(f, source);
        }
        return source;
    }
```

看注释，原来这个方法是个 **hook function 钩子函数**。通过调试得知静态对象 **onObservableAssembly**默认为 **null**， 所以此方法直接返回传入的参数 **source**。

> **钩子函数**在RxJava中出现相当多，在系统没有调用函数之前，钩子就先捕获该消息，得到控制权。这时候钩子程序既可以改变该程序的执行，插入我们要执行的代码片段，还可以强制结束消息的传递。我们可以用作全局的监听。也可以做坏事，比如在下面程序中，把observable设置null，那就肯定会报空指针异常，不过我们还是不要这么干O(∩_∩)O
>
> ```java
>  RxJavaPlugins.setOnObservableAssembly(new Function<Observable, Observable>() {
>             @Override
>             public Observable apply(Observable observable) throws Throwable {
>                 System.out.println("apply : " + observable);
>                 observable = null;
>                 return observable;
>             }
>         });
> ```
>
> 

*onObservableAssembly* 可以通过静态方法 **RxJavaPlugins. setOnObservableAssembly ()**设置全局的 Hook 函数。

现在我们明白了: 

```java
Observable observable = Observable.create(new ObservableOnSubscribe<String>() {
    @Override
    public void subscribe(@NonNull ObservableEmitter<String> emitter) throws Throwable {
        emitter.onNext("hello");
    }
});
```

等价于

```java
Observable observable =new ObservableCreate<>(new ObservableOnSubscribe<String>() {
    @Override
    public void subscribe(@NonNull ObservableEmitter<String> emitter) throws Throwable {
        emitter.onNext("hello");
    }
});
```

好了，至此我们明白了，事件的源就是 **new ObservableCreate()**对象，将**ObservableOnSubscribe** 作为参数传递给 **ObservableCreate** 的构造函数。事件是由接口 **ObservableOnSubscribe** 的 **subscribe** 方法上产的，至于何时生产事件，稍后再分析。

**Observable创建过程时序图如下：**

![微信图片_20220511222722](https://s2.loli.net/2022/05/11/lTzKd7Xe93pyPIs.png)

### **Observer**

**Observer** **是数据的下游，即事件消费者**

```java
public interface Observer<@NonNull T> {

    void onSubscribe(@NonNull Disposable d);

    void onNext(@NonNull T t);

    void onError(@NonNull Throwable e);

    void onComplete();

}
```

上游发送的事件就是再这几个方法中被消费的。至于上游何时发送事件、如何发送，我们稍后再看



### **subscribe**

observable.subscribe(observer)这个方法就是实现订阅的，是将观察者(observer)与被观察者(observable)连接起来的方法。只有 subscribe 方法执行后，上游产生的事件才能被下游接收并处理。其实自然的方式应该是 observer 订阅(subscribe) observable, 但这样会打断 rxjava 的链式结构。所以采用相反的方式。

```java
    public final void subscribe(@NonNull Observer<? super T> observer) {
        ...
        //hook 函数 ，默认直接返回observer
        observer = RxJavaPlugins.onSubscribe(this, observer);
        // 这个才是真正实现订阅的方法。
        subscribeActual(observer);
        ...
    }
```

```java
//抽象方法，所以需要到实现类中去看具体实现，也就是说实现是在上文中提到的 ObservableCreate    
protected abstract void subscribeActual(@NonNull Observer<? super T> observer);
```

接下来我们来看 **ObservableCreate.java**： 

**构造函数**

```java
   public ObservableCreate(ObservableOnSubscribe<T> source) {
        this.source = source;//事件源，生产事件的接口，由我们自己实现
    }
```

重点是这个**subscribeActual**方法：

```java
@Override
protected void subscribeActual(Observer<? super T> observer) {
    //发射器
    CreateEmitter<T> parent = new CreateEmitter<>(observer);
    //直接回调了观察者的 onSubscribe，所以这个是一订阅就马上触发。
    observer.onSubscribe(parent);

    try {
        // 调用了事件源 subscribe 方法生产事件，同时将发射器传给事件源；
        // 现在明白了，数据源生产事件的 subscribe 方法只有在 observable.subscribe(observer)被执行后才执行的。 换言之，事件流是在订阅后才产生的；
        // 而 observable 被创建出来时并不生产事件，同时也不发射事件；
        source.subscribe(parent);
    } catch (Throwable ex) {
        Exceptions.throwIfFatal(ex);
        parent.onError(ex);
    }
}
```

**现在我们明白了，数据源生产事件的 subscribe 方法只有在observable.subscribe(observer)被执行后才执行的。 换言之，事件流是在订阅后才产生的。而 observable 被创建出来时并不生产事件，同时也不发射事件。**



接下来我们再来看看事件是如何被发射出去，同时 observer 是如何接收到发射的事件的



```java
CreateEmitter<T> parent = new CreateEmitter<T>(observer);
```



**CreateEmitter** 实现了 **ObservableEmitter** 接口，同时 **ObservableEmitter** 接口又继承了**Emitter** 接口。

**CreateEmitter** 还实现了 **Disposable** 接口，这个 disposable 接口是用来判断是否中断事件发射的。

从名称上就能看出，这个是发射器，故名思议是用来发射事件的，正是它将上游产生的事件发射到下游的。

**Emitter** 是事件源与下游的桥梁。

**CreateEmitter** 主要包括方法：

```java
void onNext(@NonNull T value);
void onError(@NonNull Throwable error);
void onComplete();
public void dispose() ;
public boolean isDisposed();
```

是不是跟 observer 的方法很像？

我们来看看 CreateEmitter 中这几个方法的具体实现：

只列出关键代码

```java
   static final class CreateEmitter<T> extends AtomicReference<Disposable> implements ObservableEmitter<T>, Disposable {

        private static final long serialVersionUID = -3434801548987643227L;

        final Observer<? super T> observer;

        CreateEmitter(Observer<? super T> observer) {
            this.observer = observer;
        }

        @Override
        public void onNext(T t) {
            if (t == null) {
                onError(ExceptionHelper.createNullPointerException("onNext called with a null value."));
                return;
            }
            //判断事件是否需要被丢弃
            if (!isDisposed()) {
                // 调用Emitter的onNext，它会直接调用observer的 onNext
                observer.onNext(t);
            }
        }

        @Override
        public boolean tryOnError(Throwable t) {
            if (t == null) {
                t = ExceptionHelper.createNullPointerException("onError called with a null Throwable.");
            }
            if (!isDisposed()) {
                try {
                    // 调用 Emitter 的 onError，它会直接调用 observer 的 onError
                    observer.onError(t);
                } finally {
                    // 当 onError 被触发时，执行 dispose(), 后续 onNext，onError， onComplete 就不会继续发射事件了
                    dispose();
                }
                return true;
            }
            return false;
        }

        @Override
        public void onComplete() {
            if (!isDisposed()) {
                try {
                    //调用 Emitter 的 onComplete，它会直接调用 observer 的 onComplete
                    observer.onComplete();
                } finally {
                    // 当 onComplete 被触发时，也会执行 dispose(), 后续 onNext，onError，onComplete同样不会继续发射事件了
                    dispose();
                }
            }
        }
    }
```

**CreateEmitter** 的 **onError** 和 **onComplete** 方法任何一个执行完都会执行 **dispose()**中断事件发射，所以 observer 中的 **onError** 和 **onComplete** 也只能有一个被执行。

现在我们可以知道，事件是如何被发射给下游的。当订阅成功后，数据源**ObservableOnSubscribe** 开始生产事件，调用**Emitter**的**onNext**，**onComplete**向下游发射事件。

**Emitter** 包含了 **observer** 的引用，又调用了**observer** **onNext**，**onComplete**，这样下游observer 就接收到了上游发射的数据。



**Observable 与 Observer 订阅的过程 重要步骤**：

![微信图片_20220511222835](https://s2.loli.net/2022/05/11/ujY4w653xIpzm1q.png)



**Observable 与 Observer 订阅的过程时序图如下：**

![微信图片_20220511222859](https://s2.loli.net/2022/05/11/589kmwOuUsGHDj7.png)

****

### 总结

**Rxjava 的流程大概是：**

1. **Observable.create** **创建事件源，但并不生产也不发射事件。**

2. **实现** **observer** **接口，但此时没有也无法接受到任何发射来的事件。**

3. 订阅 **observable.subscribe(observer)**， 此时会调用具体 **Observable**的实现类中的**subscribeActual** 方法，此时会才会真正触发事件源生产事件，事件源生产出来的事件通过 **Emitter**的 **onNext**，**onError**，**onComplete**发射给 **observer** 对应的方法由下游 **observer**消费掉。从而完成整个事件流的处理。
4. **observer** 中的 onSubscribe 在订阅时即被调用，并传回了 **Disposable**， **observer** 中可以利用 **Disposable** 来随时中断事件流的发射。



## 二，map转换

**我们知道了RxJava简单使用的原理之后，我们跟着就要学习操作符的使用了，可是操作符有那么多？我们怎么学呢？**

**其实我们只要搞懂一个操作符的原理，我们就会懂得其他操作符的原理，进而了解整个RxJava的原理。**

接下来，我们来研究**map**操作符

![微信图片_20220511230923](https://s2.loli.net/2022/05/11/tYmsgTbfMq4o8Gz.png)

使用如下：

```java
Observable.create(new ObservableOnSubscribe<String>() {
    @Override
    public void subscribe(@NonNull ObservableEmitter<String> emitter) throws Throwable {
        emitter.onNext("hello");
    }
}).map(new Function<String, String>() {
    @Override
    public String apply(String s) throws Throwable {
        //可以把传入进来的s进行小写转换，这就是map的功能，能把一个圆形变成一个方形
        return s.toLowerCase(Locale.ROOT);
    }
}).subscribe(new Observer<String>() {
    @Override
    public void onSubscribe(@NonNull Disposable d) {
        Log.d(TAG, "onSubscribe() called with: d = [" + d + "]");
    }

    @Override
    public void onNext(@NonNull String s) {
        Log.d(TAG, "onNext() called with: s = [" + s + "]");
    }

    @Override
    public void onError(@NonNull Throwable e) {
        Log.d(TAG, "onError() called with: e = [" + e + "]");
    }

    @Override
    public void onComplete() {
        Log.d(TAG, "onComplete() called");
    }
});
```





现在，我们就走进map操作符的源码

```java
public final <R> Observable<R> map(@NonNull Function<? super T, ? extends R> mapper) {
    Objects.requireNonNull(mapper, "mapper is null");
    return RxJavaPlugins.onAssembly(new ObservableMap<>(this, mapper));
}
```

我们现在又看到了熟悉的钩子hook函数，RxJava中的钩子函数真的是无处不在，在此，我们默认知道其实这个函数就会返回**new ObservableMap<>(this, mapper)** 这个对象。想都不用想我们知道这个**ObservableMap**其实也是**Observable**的子类



我们点进去**ObservableMap**的源码看一下

```java
public final class ObservableMap<T, U> extends AbstractObservableWithUpstream<T, U> {
    final Function<? super T, ? extends U> function;

    public ObservableMap(ObservableSource<T> source, Function<? super T, ? extends U> function) {
        // source是上游Observable
        super(source);
        this.function = function;
    }

    @Override
    public void subscribeActual(Observer<? super U> t) {
        // 调用了上游Observable（即ObservableCreate）的subscribe方法，传入new出来的MapObserver对象，第一个参数是下游Observer，第二个参数是Function泛型接口
        source.subscribe(new MapObserver<T, U>(t, function));
    }
}    
```

上面ObservableMap就做了三件事

1. 在构造方法中，将传入的Observable也就是本身抛给父类（ObservableSource是Observable的父类，所以可以接受）
2. 对转换逻辑funtion进行保存
3. 重写**subscribeActual**()方法并在其中实现**订阅**



我们重点看**subscribeActual**的实现，source指的是上游自定义source（即ObservableCreate），按照之前我们分析，应该是 source.subscribe(Observer)，

刚好**MapObserver**这个也是**Observer**的子类，所以没问题。

创建**MapObserver**需要两个参数，第一个参数是自定义观察者（下游Observer或者又叫终点），第二个参数是转换逻辑的funtion。



我们现在点进去自定义source（**ObservableCreate**）的subscribe方法

```java
@Override
protected void subscribeActual(Observer<? super T> observer) {//第一层包裹
    //第二层包裹
    CreateEmitter<T> parent = new CreateEmitter<>(observer);
    observer.onSubscribe(parent);

    try {
        source.subscribe(parent);
    } catch (Throwable ex) {
        Exceptions.throwIfFatal(ex);
        parent.onError(ex);
    }
}
```

发现它**在第一层包裹的基础上，又给它封了一层包裹**，也就是把第一层包裹作为参数传入了第二层包裹即**发射器**。



也就是说最终的终点（自定义观察者）**经历了两次封装**，第一次是封装为`MapObserver`，我们称之为第一层包裹，第二次是封装为`CreateEmitter`，我们称之为第二层包裹。



然后我们来看我们的自定义source发送的事件是怎么流入到终点的。

```java
Observable.create(new ObservableOnSubscribe<String>() {
    @Override
    public void subscribe(@NonNull ObservableEmitter<String> emitter) throws Throwable {
        emitter.onNext("hello");
    }
})
```

我们发射的最先是由**CreateEmitter**中开启。我们查看**CreateEmitter**这个类的**onNext**()方法：

```
@Override
public void onNext(T t) {
    if (t == null) {
        onError(ExceptionHelper.createNullPointerException("onNext called with a null value."));
        return;
    }
    if (!isDisposed()) {
        observer.onNext(t);
    }
}
```

发现它调用了**observer**的**onNext**方法，并且把我们传入的参数也作为参数传进去，这个**observer**是下一层，而不是自定义观察者。它的下一层就是**ObservableMap**，我们现在进入**ObservableMap**看一下



```java
@Override
public void onNext(T t) {
    if (done) {
        return;
    }

    if (sourceMode != NONE) {
        downstream.onNext(null);
        return;
    }

    U v;

    try {
        //mapper.apply(t) 进行变换，用v接受变换后的值
        v = Objects.requireNonNull(mapper.apply(t), "The mapper function returned a null value.");
    } catch (Throwable ex) {
        fail(ex);
        return;
    }
    //调用下一层的onNext方法，并把变换后的的值v作为参数传入
    downstream.onNext(v);
}
```

 首先将我们传入的值进行了一个**变换**，即apply方法，然后调用下游的`onNext`方法将变换后的值传过去。这里我们的下游就是终点，即**自定义观察者**。所以就到头了。



**装饰模式**

假如用到了两个`map`操作符，`create`方法返回的是`ObservableCreate`对象，然后调用`map`方法，相当于将`ObservableCreate`用`ObservableMap`包起来，然后又调用一次`map`方法，相当于用`ObservableMap`将`ObservableMap`包起来。用图表示就是这样子

![微信图片_20220511234549](https://s2.loli.net/2022/05/11/ya23PBxz4c5ubQ8.png)





**总结：**



![微信图片_20220511234448](https://s2.loli.net/2022/05/11/YfNCDoJbQmyzaFB.png)





## 三，线程调度

 

Android 的 UI 线程是不能做网络操作，也不能做耗时操作，

所以一般我们把网络或耗时操作都放在非 UI 线程中执行。

RxJava强 大的线程调度能力能很快很好进行线程切换。

```java
Observable.create(new ObservableOnSubscribe<String>() {
    @Override
    public void subscribe(@NonNull ObservableEmitter<String> emitter) throws Throwable {
        emitter.onNext("hello");
    }
}).subscribeOn(Schedulers.io()).observeOn(AndroidSchedulers.mainThread()).subscribe(new Observer<String>() {
    @Override
    public void onSubscribe(@NonNull Disposable d) {
        Log.d(TAG, "onSubscribe() called with: d = [" + d + "]");
    }

    @Override
    public void onNext(@NonNull String s) {
        Log.d(TAG, "onNext() called with: s = [" + s + "]");
    }

    @Override
    public void onError(@NonNull Throwable e) {
        Log.d(TAG, "onError() called with: e = [" + e + "]");
    }

    @Override
    public void onComplete() {
        Log.d(TAG, "onComplete() called");
    }
});
```

### **线程调度**（被观察者） **subscribeOn**

> **Scheduler分类**
>
> > | **调度器类型**                 | **效果**                                                     |
> > | ------------------------------ | ------------------------------------------------------------ |
> > | Schedulers.computation()       | 用于计算任务，如事件循环或和回调处理，不要用于IO操作(IO操作请使用Schedulers.io())；默认线程数等于处理器的数量 |
> > | Schedulers.from(executor)      | 使用指定的Executor作为调度器                                 |
> > | Schedulers.immediate( )        | 在当前线程立即开始执行任务                                   |
> > | Schedulers.io( )               | 用于IO密集型任务                                             |
> > | Schedulers.newThread( )        | 为每个任务创建一个新线程                                     |
> > | Schedulers.trampoline( )       | 当其它排队的任务完成后，在当前线程排队开始执行               |
> > | AndroidSchedulers.mainThread() | 用于Android的UI更新操作                                      |



首先我们先分析下 **Schedulers.io()**这个函数是什么

```java
@NonNull
public static Scheduler io() {
    return RxJavaPlugins.onIoScheduler(IO);
}
```

老熟人hook函数，我们直接看**IO**是啥

**IO** 是个 static 变量，初始化的地方是**Schedulers**的静态代码块中

```java
IO = RxJavaPlugins.initIoScheduler(new IOTask());
```

等价于

```
io() = new IOTask().call();
```

继续看看 **IOTask**

```java
static final class IOTask implements Supplier<Scheduler> {
    @Override
    public Scheduler get() {
        return IoHolder.DEFAULT;
    }
}
```

综合以上，得出结论

```java
Schedulers.io() = new IoScheduler()
```

好了，排除了其他干扰代码，接下来看看 IoScheduler()是什么了



**IoScheduler** 看名称就知道是个 **IO 线程调度器**，根据代码注释得知，它就是一个用来创建

和缓存线程的**线程池**。看到这个豁然开朗了，原来 Rxjava 就是通过这个调度器来调度线程

的，至于具体怎么实现我们接着往下看

```java
   //无参构造函数
   public IoScheduler() {
        this(WORKER_THREAD_FACTORY);
    }

    //有参构造函数
    public IoScheduler(ThreadFactory threadFactory) {
        this.threadFactory = threadFactory;
        this.pool = new AtomicReference<>(NONE);
        start();
    }
    
    @Override
    public void start() {
        CachedWorkerPool update = new CachedWorkerPool(KEEP_ALIVE_TIME, KEEP_ALIVE_UNIT, threadFactory);
        if (!pool.compareAndSet(NONE, update)) {
            update.shutdown();
        }
    }
    
   //CachedWorkerPool构造函数
    CachedWorkerPool(long keepAliveTime, TimeUnit unit, ThreadFactory threadFactory) {
            this.keepAliveTime = unit != null ? unit.toNanos(keepAliveTime) : 0L;
            this.expiringWorkerQueue = new ConcurrentLinkedQueue<>();
            this.allWorkers = new CompositeDisposable();
            this.threadFactory = threadFactory;

            ScheduledExecutorService evictor = null;
            Future<?> task = null;
            if (unit != null) {
                //EVICTOR_THREAD_FACTORY 是名为 RxCachedWorkerPoolEvictor 的清除线程
                evictor = Executors.newScheduledThreadPool(1, EVICTOR_THREAD_FACTORY);
                task = evictor.scheduleWithFixedDelay(this, this.keepAliveTime, this.keepAliveTime, TimeUnit.NANOSECONDS);
            }
            evictorService = evictor;
            evictorTask = task;
    }
```

从上面的代码可以看出，**new IoScheduler()**后 Rxjava 会创建 **CachedWorkerPool** 的线程池，同时也创建并运行了一个名为 **RxCachedWorkerPoolEvictor** 的**清除线程**，主要作用是清除不再使用的一些线程。但目前只创建了线程池并没有实际的 thread，所以 Schedulers.io()相当于只做了线程调度的**前期准备**。

OK，终于可以开始分析 Rxjava 是如何实现线程调度的。回看 **subscribeOn()**方法的内部实现：

```java
@CheckReturnValue
@SchedulerSupport(SchedulerSupport.CUSTOM)
@NonNull
public final Observable<T> subscribeOn(@NonNull Scheduler scheduler) {
    Objects.requireNonNull(scheduler, "scheduler is null");
    return RxJavaPlugins.onAssembly(new ObservableSubscribeOn<>(this, scheduler));
}
```

很熟悉的代码 **RxJavaPlugins.onAssembly**,上一篇已经分析过这个方法，就是个 **hook function**， 等价于直接 return new ObservableSubscribeOn<T>(this, scheduler);， 现在知道了这里的 scheduler 其实就是 **IoScheduler**。



跟踪代码进入 **ObservableSubscribeOn**，可以看到这个 **ObservableSubscribeOn** 继承自 **Observable**，并且扩展了一些属性，增加了

**scheduler**。 这就是典型的**装饰模式**，Rxjava 中大量用到了装饰模式，后面还会经常看到这种 wrap 类。



上面我们已经知道了 **Observable.subscribe()**方法最终都是调用了对应的实现类的**subscribeActual** 方法。我们重点分析下 **subscribeActual**: 



```java
@Override
public void subscribeActual(final Observer<? super T> observer) {
    final SubscribeOnObserver<T> parent = new SubscribeOnObserver<>(observer);
    //没有任何线程调度，直接调用的，所以下游的 onSubscribe 方法没有切换线程,
    //所以我们明白了为什么只有 onSubscribe 还运行在 main 线程 
    observer.onSubscribe(parent);
    parent.setDisposable(scheduler.scheduleDirect(new SubscribeTask(parent)));
}
```

**SubscribeOnObserver** 也是装饰模式的体现， 是对下游 observer 的一个 wrap，只是添加了 **Disposable** 的管理。

接下来分析最重要的 **scheduler.scheduleDirect(new SubscribeTask(parent))**

```java
//这个类很简单，就是一个 Runnable，最终运行上游的 subscribe 方法
final class SubscribeTask implements Runnable {
    private final SubscribeOnObserver<T> parent;

    SubscribeTask(SubscribeOnObserver<T> parent) {
        this.parent = parent;
    }

    @Override
    public void run() {
        source.subscribe(parent);
    }
}
```

```java
@NonNull
public Disposable scheduleDirect(@NonNull Runnable run, long delay, @NonNull TimeUnit unit) {
    //IoSchedular 中的 createWorker()
    final Worker w = createWorker();

    //hook decoratedRun=run
    final Runnable decoratedRun = RxJavaPlugins.onSchedule(run);

    //decoratedRun的 wrap，增加了 Dispose 的管理
    DisposeTask task = new DisposeTask(decoratedRun, w);

    // 线程调度
    w.schedule(task, delay, unit);

    return task;
}
```

回到 **IoScheduler**

```java
@NonNull
@Override
public Worker createWorker() {
    // 工作线程是在此时创建的
    return new EventLoopWorker(pool.get());
}
```

```java
static final class EventLoopWorker extends Scheduler.Worker {

    @NonNull
    @Override
    public Disposable schedule(@NonNull Runnable action, long delayTime, @NonNull TimeUnit unit) {
        if (tasks.isDisposed()) {
            // don't schedule, we are unsubscribed
            return EmptyDisposable.INSTANCE;
        }
        //action 中就包含上游 subscribe 的 runnable
        return threadWorker.scheduleActual(action, delayTime, unit, tasks);
    }
}
```

最终线程是在这个方法内调度并执行的。



```java
@NonNull
public ScheduledRunnable scheduleActual(final Runnable run, long delayTime, @NonNull TimeUnit unit, @Nullable DisposableContainer parent) {
    //decoratedRun = run, 包含上游 subscribe 方法的 runnable
    Runnable decoratedRun = RxJavaPlugins.onSchedule(run);

    //decoratedRun 的 wrap，增加了 dispose 的管理
    ScheduledRunnable sr = new ScheduledRunnable(decoratedRun, parent);

    if (parent != null) {
        if (!parent.add(sr)) {
            return sr;
        }
    }

    // 最终 decoratedRun 被调度到之前创建或从线程池中取出的线程 也就是说在RxCachedThreadScheduler-x 运行
    Future<?> f;
    try {
        if (delayTime <= 0) {
            f = executor.submit((Callable<Object>)sr);
        } else {
            f = executor.schedule((Callable<Object>)sr, delayTime, unit);
        }
        sr.setFuture(f);
    } catch (RejectedExecutionException ex) {
        if (parent != null) {
            parent.remove(sr);
        }
        RxJavaPlugins.onError(ex);
    }

    return sr;
}
```

至此我们终于明白了 Rxjava 是如何调度线程并执行的，通过 subscribeOn 方法将上游生产事件的方法运行在指定的调度线程中。



上游生产者已被调度到RxCachedThreadScheduler-1线程中，同时发射事件并没有切换线程，所以发射后消费事件的 onNext onErro onComplete 也在

RxCachedThreadScheduler-1 线程中。



**图解**

![图片1](https://s2.loli.net/2022/05/12/zQ9oUSPLDWlctEj.png)

![图片2](https://s2.loli.net/2022/05/12/BohX1ZmNTp5A34a.png)

#### 概括

1. Schedulers.io()等价于 new IoScheduler()。
2. new IoScheduler() Rxjava 创建了**线程池**，为后续创建线程做准备，同时创建并运行了一个**清理线程 RxCachedWorkerPoolEvictor**，定期执行清理任务。
3. subscribeOn()返回一个 **ObservableSubscribeOn** 对象，它是 **Observable** 的一个**装饰类**，增加了 **scheduler**。
4. 调用 **subscribe**()方法，在这个方法调用后，**subscribeActual**()被调用，才真正执行了IoSchduler 中的 **createWorker**()创建线程并运行，最终将上游 Observable 的 subscribe()方法调度到新创建的线程中运行。
5. 因为 RxJava 最终能影响 **ObservableOnSubscribe** 这个匿名实现接口的运行环境的只能是最后一次运行的 **subscribeOn()** ，又因为 RxJava 订阅的时候是**从下往上**订阅，所以从上往下第一个 **subscribeOn()** 就是最后运行的，这就造成了写多个 subscribeOn() 并没有什么用的现象。

### **线程调度（观察者）** **observeOn**

#### **AndroidSchedulers.mainThread()**

先来看看 AndroidSchedulers.mainThread()是什么？

```java
//在主线程执行任务的 scheduler
public static Scheduler mainThread() {
    return RxAndroidPlugins.onMainThreadScheduler(MAIN_THREAD);
}
```

```java
private static final Scheduler MAIN_THREAD =
    RxAndroidPlugins.initMainThreadScheduler(() -> MainHolder.DEFAULT);
```

```java
private static final class MainHolder {
    static final Scheduler DEFAULT
        = new HandlerScheduler(new Handler(Looper.getMainLooper()), true);
}
```

```java
public static Scheduler initMainThreadScheduler(Callable<Scheduler> scheduler) {
    if (scheduler == null) {
        throw new NullPointerException("scheduler == null");
    }
    Function<Callable<Scheduler>, Scheduler> f = onInitMainThreadHandler;
    if (f == null) {
        return callRequireNonNull(scheduler);
    }
    return applyRequireNonNull(f, scheduler);
}
```

代码很简单，这个 **AndroidSchedulers.mainThread()**想当于 **new HandlerScheduler(new** **Handler(Looper.getMainLooper()))**,原来是利用 Android 的 **Handler** 来调度到 **main** 线程的。

我们再看看 **HandlerScheduler**，它与我们上节分析的 **IOScheduler** 类似，都是继承自**Scheduler**,所以 AndroidSchedulers.mainThread()其实就是是创建了一个运行在 **main** thread 上的 scheduler。



#### **observeOn**

我们看看这个操作符的源码

```java
public final Observable<T> observeOn(@NonNull Scheduler scheduler) {
    return observeOn(scheduler, false, bufferSize());
}
```

```java
public final Observable<T> observeOn(@NonNull Scheduler scheduler, boolean delayError, int bufferSize) {
    Objects.requireNonNull(scheduler, "scheduler is null");
    ObjectHelper.verifyPositive(bufferSize, "bufferSize");
    return RxJavaPlugins.onAssembly(new ObservableObserveOn<>(this, scheduler, delayError, bufferSize));
}
```

重点是这个 **new ObservableObserveOn**,和之前研究的**ObservableSubscribeOn**继承自同一个父类。

重点还是这个方法，我们前文已经提到了，Observable 的 **subscribe** 方法最终都是调用subscribeActual 方法。下面看看这个方法的实现：

```java
@Override
protected void subscribeActual(Observer<? super T> observer) {
    // scheduler 就是前面提到的 HandlerScheduler，所以进入 else 分支
    if (scheduler instanceof TrampolineScheduler) {
        source.subscribe(observer);
    } else {
        //创建 HandlerWorker
        Scheduler.Worker w = scheduler.createWorker();

        //调用上游 Observable 的 subscribe，将订阅向上传递
        source.subscribe(new ObserveOnObserver<>(observer, w, delayError, bufferSize));
    }
}
```

从上面代码可以看到使用了 **ObserveOnObserver** 类对 **observer** 进行装饰，好了，我们再来看看 **ObserveOnObserver**。

我们已经知道了，事件源发射的事件，是通过 observer 的 **onNext**,**onError**,**onComplete** 发射到下游的。所以看看 **ObserveOnObserver** 的这三个方法是如何实现的。我们来看onNext 方法：

```java
@Override
public void onNext(T t) {
    if (done) {
        return;
    }

    //如果是非异步方式，将上游发射的时间加入到队列
    if (sourceMode != QueueDisposable.ASYNC) {
        queue.offer(t);
    }
    schedule();
}
```

```java
void schedule() {
    //保证只有唯一任务在运行
    if (getAndIncrement() == 0) {
        //调用的就是 HandlerWorker 的 schedule 方法
        worker.schedule(this);
    }
}
```

```java
@Override
@SuppressLint("NewApi") // Async will only be true when the API is available to call.
public Disposable schedule(Runnable run, long delay, TimeUnit unit) {
    if (run == null) throw new NullPointerException("run == null");
    if (unit == null) throw new NullPointerException("unit == null");

    if (disposed) {
        return Disposable.disposed();
    }

    run = RxJavaPlugins.onSchedule(run);

    ScheduledRunnable scheduled = new ScheduledRunnable(handler, run);

    Message message = Message.obtain(handler, scheduled);
    message.obj = this; // Used as token for batch disposal of this worker's runnables.

    if (async) {
        message.setAsynchronous(true);
    }

    handler.sendMessageDelayed(message, unit.toMillis(delay));

    // Re-check disposed state for removing in case we were racing a call to dispose().
    if (disposed) {
        handler.removeCallbacks(scheduled);
        return Disposable.disposed();
    }

    return scheduled;
}
```

**schedule** 方法将传入的 run 调度到对应的 handle 所在的线程来执行，这个例子里就是有main 线程来完成。 再回去看看前面传入的 run 吧。

回到 ObserveOnObserver 中的 run 方法：

```java
@Override
public void run() {
    if (outputFused) {
        drainFused();
    } else {
        drainNormal();
    }
}
```

```java
void drainNormal() {
    int missed = 1;

    final SimpleQueue<T> q = queue;
    final Observer<? super T> a = downstream;

    for (;;) {
        if (checkTerminated(done, q.isEmpty(), a)) {
            return;
        }

        for (;;) {
            boolean d = done;
            T v;

            try {
                // 从队列中 queue 中取出事件
                v = q.poll();
            } catch (Throwable ex) {
                Exceptions.throwIfFatal(ex);
                disposed = true;
                upstream.dispose();
                q.clear();
                a.onError(ex);
                worker.dispose();
                return;
            }
            boolean empty = v == null;

            if (checkTerminated(d, empty, a)) {
                return;
            }

            if (empty) {
                break;
            }

            //调用下游 observer 的 onNext 将事件 v 发射出去
            a.onNext(v);
        }

        missed = addAndGet(-missed);
        if (missed == 0) {
            break;
        }
    }
}
```

至此我们明白了 RXjava 是如何调度消费者线程了。



#### 概括

Rxjava 调度消费者现在的流程，以 observeOn(AndroidSchedulers.mainThread())为例。

1. AndroidSchedulers.mainThread()先创建一个包含 **handler** 的 **Scheduler**, 这个 handler 是主线程的 handler。

2. **observeOn** 方法创建 **ObservableObserveOn**,它是上游 **Observable** 的一个装饰类，其中包含前面创建的 **Scheduler** 和 **bufferSize** 等.

3. 当**订阅方法 subscribe** 被调用后，ObservableObserveOn 的 **subscribeActual** 方法创建**Scheduler.Worker** 并调用**上游**的 **subscribe** 方法，同时将自身接收的参数**observer**用**装饰**类 **ObserveOnObserver** 装饰后传递给上游。

4. 当上游调用被 **ObserveOnObserver** 的 onNext、onError 和 onComplete 方法时，**ObserveOnObserver** 将上游发送的事件通通加入到队列 **queue** 中，然后再调用 **scheduler**将处理事件的方法调度到对应的线程中（本例会调度到 main thread）。 处理事件的方法将**queue 中保存的事件取出来**，调用下游原始的 **observer 再发射出去**。

5. 经过以上流程，下游处理事件的消费者线程就运行在了 observeOn 调度后的 thread 中。



### 线程总结

- Rxjava 的 **subscribe** 方法是由**下游一步步向上游进行传递**的。会调用上游的 subscribe，直到调用到事件源。如： **source.subscribe(xxx);**而上游的 source 往往是经过装饰后的 Observable, Rxjava 就是利用ObservableSubscribeOn 将 subscribe 方法调度到了指定线程运行，生产者线程最终会运行在被调度后的线程中。但多次调用 subscribeOn 方法会怎么样呢？ 我们知道因为 subscribe方法是由下而上传递的，所以事件源的生产者线程最终都只会运行在第一次执行subscribeOn 所调度的线程中，换句话就是多次调用 subscribeOn 方法，只有第一次有效。

- Rxjava **发射**事件是**由上而下**发射的，上游的 **onNext、onError、onComplete** 方法会调用下游传入的 **observer** 的对应方法。往往下游传递的 observer 对象也是经过装饰后的observer 对象。Rxjava 就是利用 **ObserveOnObserver** 将执行线程调度后，再调用下游对应的 onNext、onError、onComplete 方法，这样下游消费者就运行再了指定的线程内。 那么多次调用 observeOn 调度不同的线程会怎么样呢？ 因为事件是由上而下发射的，所以每次用 observeOn 切换完线程后，对下游的事件消费都有效，比如下游的 map 操作符。最终的事件消费线程运行在最后一个 observeOn 切换后线程中。

## 四，背压

参考https://blog.csdn.net/carson_ho/article/details/79081407

### 原理

![背压原理](https://s2.loli.net/2022/05/13/chO3gVEUj7IdJby.png)

### 控制观察者接收事件的速度

#### 异步订阅

![5.1.1](https://s2.loli.net/2022/05/13/FVoLIez9sSOgM4Y.png)

![5.1.1.2](https://s2.loli.net/2022/05/13/QYRZec291aL8vHo.png)

#### 同步订阅

同步订阅 & 异步订阅 的区别在于：

- 同步订阅中，被观察者 & 观察者工作于同1线程
- 同步订阅关系中没有缓存区

![5.1.2](https://s2.loli.net/2022/05/13/yb32qe8jRQsdMU6.png)



### 控制被观察者发送事件的速度

#### 异步订阅

![5.2](https://s2.loli.net/2022/05/13/94YjPHyB3ZACQoT.png)



#### 同步订阅

- 在同步订阅情况中使用`FlowableEmitter.requested()`时，有以下几种使用特性需要注意的：

  ![5.2.2](https://s2.loli.net/2022/05/13/b1Vs3DfpBh9yQvj.png)

### **背压策略**

##### 模式1：BackpressureStrategy.ERROR

- 问题：发送事件速度 ＞ 接收事件 速度，即流速不匹配

  > 具体表现：出现当缓存区大小存满（默认缓存区大小 = 128）、被观察者仍然继续发送下1个事件时 

- 处理方式：直接抛出异常**MissingBackpressureException**

##### 模式2：BackpressureStrategy.MISSING

- 问题：发送事件速度 ＞ 接收事件 速度，即流速不匹配

  > 具体表现是：出现当缓存区大小存满（默认缓存区大小 = 128）、被观察者仍然继续发送下1个事件时 

- 处理方式：友好提示：缓存区满了

##### 模式3：BackpressureStrategy.BUFFER

- 问题：发送事件速度 ＞ 接收事件 速度，即流速不匹配 

  > 具体表现是：出现当缓存区大小存满（默认缓存区大小 = 128）、被观察者仍然继续发送下1个事件时

- 处理方式：将缓存区大小设置成无限大 

  > 1. 即被观察者可无限发送事件观察者，但实际上是存放在缓存区 
  > 2. 但要注意内存情况，防止出现OOM

##### 模式4： BackpressureStrategy.DROP

- 问题：发送事件速度 ＞ 接收事件 速度，即流速不匹配 

  > 具体表现是：出现当缓存区大小存满（默认缓存区大小 = 128）、被观察者仍然继续发送下1个事件时

- 处理方式：超过缓存区大小（128）的事件丢弃 

  > 如发送了150个事件，仅保存第1 - 第128个事件，第129 -第150事件将被丢弃

##### 模式5：BackpressureStrategy.LATEST

- 问题：发送事件速度 ＞ 接收事件 速度，即流速不匹配 

  > 具体表现是：出现当缓存区大小存满（默认缓存区大小 = 128）、被观察者仍然继续发送下1个事件时

- 处理方式：只保存最新（最后）事件，超过缓存区大小（128）的事件丢弃 

  > 即如果发送了150个事件，缓存区里会保存129个事件（第1-第128 + 第150事件）



![6a3ffae7219b993eed20f48290136fd0](https://s2.loli.net/2022/05/13/nLDUZd86AYjKoV9.png)



## 五，常见问题

## 5.1，操作符 map 和 flatmap 的区别？

- map：【数据类型转换】将被观察者发送的事件转换为另一种类型的事件。

- flatMap：【化解循环嵌套和接口嵌套】将被观察者发送的事件序列进行拆分 & 转换 后合并成一个新的事件序列，最后再进行发送。

- concatMap：【有序】与 flatMap 的 区别在于，拆分 & 重新合并生成的事件序列 的顺序与被观察者旧序列生产的顺序一致。

  

**共同点**

- 都是依赖 Function 函数进行转换（将一个类型依据程序逻辑转换成另一种类型，根据入参和返回值）

- 都能在转换后直接被 subscribe

**区别**

- 返回结果不同

  > map 返回的是结果集，flatmap 返回的是包含结果集的 Observable 对象（返回结果不同）

- 执行顺序不同

  > map 被订阅时每传递一个事件执行一次 onNext 方法，flatmap 多用于多对多，一对多，再被转化为多个时，一般利用 from/just 进行一一分发，被订阅时将所有数据传递完毕汇总到一个 Observable 然后一一执行 onNext 方法。(如单纯用于一对一转换则和 map 相同)

- 转换对象的能力不同

  > - map 只能单一转换，单一指的是只能一对一进行转换，指一个对象可以转化为另一个对象但是不能转换成对象数组。
  >
  > - flatmap 既可以单一转换也可以一对多/多对多转换，flatmap 要求返回 Observable，因此可以再内部进行事件分发，逐个取出单一对象。

## 5.2，暂未整理




