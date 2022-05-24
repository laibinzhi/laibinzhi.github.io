---
title: JVM总结二：深入理解对象
date: 2022-05-24 16:26:18
tags:
  - Android
  - Java  
  - JVM 
---


# JVM总结二：深入理解对象

## 一，虚拟机中对象的创建过程

![虚拟机中对象的创建过程](https://s2.loli.net/2022/05/23/xNDS6CWh1VLlvMG.png)

### 检查加载

首先检查这个指令的参数是否能在**常量池**中定位到一个**类的符号引用**（**符号引用**：符号引用以一组符号来描述所引用的目标），并且检查类是否已经被加载、解析和初始化过。

### 分配内存

接下来虚拟机将为新生对象分配内存。为对象分配空间的任务等同于把一块确定大小的内存从Java堆中划分出来。

#### 指针碰撞

如果Java堆中内存是绝对规整的，所有用过的内存都放在一边，空闲的内存放在另一边，中间放着一个指针作为分界点的指示器，那所分配内存就仅仅是把那个指针向空闲空间那边挪动一段与对象大小相等的距离，这种分配方式称为“**指针碰撞**”。

![指针碰撞](https://s2.loli.net/2022/05/23/Xy7GKZL5JDFaIMH.png)

#### 空闲列表

如果Java堆中的内存并不是规整的，已使用的内存和空闲的内存相互交错，那就没有办法简单地进行指针碰撞了，虚拟机就必须维护一个列表，记录上哪些内存块是可用的，在分配的时候从列表中找到一块足够大的空间划分给对象实例，并更新列表上的记录，这种分配方式称为“***空闲列表***”。

![空闲列表](https://s2.loli.net/2022/05/23/mNx9u6F7KcCtBSb.png)


<!--more-->



#### 如何选择指针碰撞和空闲列表？

选择哪种分配方式由**Java堆**是否规整决定，而Java堆是否规整又由所采用的**垃圾收集器**是否带有**压缩整理**功能决定。

如果是**Serial**、**ParNew**等带有压缩的整理的垃圾回收器的话，系统采用的是**指针碰撞**，既简单又高效。

如果是使用**CMS**这种不带压缩（整理）的垃圾回收器的话，理论上只能采用较复杂的空闲列表。

#### 并发安全

除如何划分可用空间之外，还有另外一个需要考虑的问题是对象创建在虚拟机中是非常频繁的行为，即使是仅仅修改一个指针所指向的位置，在并发情况下也并不是线程安全的，可能出现正在给对象A分配内存，指针还没来得及修改，对象B又同时使用了原来的指针来分配内存的情况。



#### CAS机制

解决这个问题有两种方案，一种是对分配内存空间的动作进行同步处理——实际上虚拟机采用CAS配上失败重试的方式保证更新操作的原子性；



#### 本地线程分配缓冲TLAB

另一种是把内存分配的动作按照线程划分在不同的空间之中进行，即每个线程在Java堆中预先分配一小块私有内存，也就是**本地线程分配缓冲（Thread Local Allocation Buffer,TLAB）**，JVM在线程初始化时，同时也会申请一块指定大小的内存，只给当前线程使用，这样每个线程都单独拥有一个Buffer，如果需要分配内存，就在自己的Buffer上分配，这样就不存在竞争的情况，可以大大提升分配效率，当Buffer容量不够的时候，再重新从Eden区域申请一块继续使用。

TLAB的目的是在为新对象分配内存空间时，让每个Java应用线程能在使用自己专属的分配指针来分配空间，减少同步开销。

TLAB只是让每个线程有私有的分配指针，但底下存对象的内存空间还是给所有线程访问的，只是其它线程无法在这个区域分配而已。当一个TLAB用满（分配指针top撞上分配极限end了），就新申请一个TLAB。

**参数：**

-XX:+UseTLAB

允许在年轻代空间中使用线程本地分配块（TLAB）。默认情况下启用此选项。要禁用TLAB，请指定-XX:-UseTLAB。

https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html



### 内存空间初始化

（注意不是构造方法）内存分配完成后，虚拟机需要将分配到的内存空间都初始化为零值(如int值为0，boolean值为false等等)。这一步操作保证了对象的实例字段在Java代码中可以不赋初始值就直接使用，程序能访问到这些字段的数据类型所对应的零值。

### 设置

接下来，虚拟机要对对象进行必要的设置，例如这个对象是哪个类的实例、如何才能找到类的元数据信息（Java classes在Java hotspot VM内部表示为类元数据）、对象的哈希码、对象的GC分代年龄等信息。这些信息存放在对象的对象头之中。

### 初始化

在上面工作都完成之后，从虚拟机的视角来看，一个新的对象已经产生了，但从Java程序的视角来看，对象创建才刚刚开始，所有的字段都还为零值。所以，一般来说，执行new指令之后会接着把对象按照程序员的意愿进行初始化(**构造方法**)，这样一个真正可用的对象才算完全产生出来。



## 二，对象的内存布局

![对象的内存布局](https://s2.loli.net/2022/05/23/K7WsaOdABCQXD31.png)

在HotSpot虚拟机中，对象在内存中存储的布局可以分为3块区域：**对象头（Header）**、**实例数据（Instance Data）**和**对齐填充（Padding）**。

### 对象头

- 对象头包括两部分信息，第一部分用于存储对象自身的运行时数据，如**哈希码（HashCode）**、**GC分代年龄**、**锁状态标志**、**线程持有的锁**、**偏向线程ID**、**偏向时间**戳等。

- 对象头的另外一部分是**类型指针**，即对象指向它的类元数据的指针，虚拟机通过这个指针来确定这个对象是哪个类的实例。

- 如果对象是一个java数组，那么在对象头中还有一块用于记录数组长度的数据。

### 实例数据

### 对齐填充

第三部分对齐填充并不是必然存在的，也没有特别的含义，它仅仅起着占位符的作用。由于HotSpot VM的自动内存管理系统要求对对象的大小必须是**8字节的整数倍**。当对象其他数据部分没有对齐时，就需要通过对齐填充来补全。





## 三，对象的访问定位

![对象的访问定位](https://s2.loli.net/2022/05/23/wkVx4SuHtO61a8X.png)

建立对象是为了使用对象，我们的Java程序需要通过栈上的reference数据来操作堆上的具体对象。目前主流的访问方式有使用句柄和直接指针两种。

### 使用句柄

如果使用句柄访问的话，那么Java堆中将会划分出一块内存来作为**句柄池**，reference中存储的就是对象的句柄地址，而句柄中包含了对象实例数据与类型数据各自的具体地址信息。

### 直接指针

如果使用直接指针访问， reference中存储的直接就是对象地址。

### 如何选择

- 这两种对象访问方式各有优势，使用句柄来访问的最大好处就是reference中存储的是稳定的句柄地址，在对象被移动（垃圾收集时移动对象是非常普遍的行为）时只会改变句柄中的实例数据指针，而reference本身不需要修改。

- 使用直接指针访问方式的最大好处就是速度更快，它节省了一次指针定位的时间开销，由于对象的访问在Java中非常频繁，因此这类开销积少成多后也是一项非常可观的执行成本。

- 对**Sun HotSpot**而言，它是使用**直接指针**访问方式进行对象访问的。



## 四，判断对象存活

在堆里面存放着几乎所有的对象实例，垃圾回收器在对对进行回收前，要做的事情就是确定这些对象中哪些还是“存活”着，哪些已经“死去”（死去代表着不可能再被任何途径使用得对象了）

### 引用计数法

在对象中添加一个引用计数器，每当有一个地方引用它，计数器就加1，当引用失效时，计数器减1.

Python在用，但主流虚拟机没有使用，因为存在对象相互引用的情况，这个时候需要引入额外的机制来处理，这样做影响效率。



### 可达性分析

来判定对象是否存活的。这个算法的基本思路就是通过一系列的称为“**GC Roots**”的对象作为起始点，从这些节点开始向下搜索，搜索所走过的路径称为引用链（Reference Chain），当一个对象到GC Roots没有任何引用链相连时，则证明此对象是不可用的。

作为GC Roots的对象包括下面几种：

-  **虚拟机栈（栈帧中的本地变量表，即局部变量表）中引用的对象**。

- **方法区**中类**静态属性**引用的对象。

- **方法区**中**常量**引用的对象。

- 本地方法栈中**JNI（即一般说的Native方法）引用**的对象。
- JVM的内部引用（class对象、异常对象NullPointException、OutofMemoryError，系统类加载器）。
- 所有被同步锁(synchronized关键)持有的对象。
- JVM内部的JMXBean、JVMTI中注册的回调、本地代码缓存等
- JVM实现中的“临时性”对象，跨代引用的对象（在使用分代模型回收只回收部分代时）



![可达性分析](https://s2.loli.net/2022/05/23/vreHjMnUI6PgZO3.png)

## 五，Finalize方法

即使通过可达性分析判断不可达的对象，也不是“非死不可”，它还会处于“缓刑”阶段，真正要宣告一个对象死亡，需要经过两次标记过程，一次是没有找到与GCRoots的引用链，它将被第一次标记。随后进行一次筛选（如果对象覆盖了finalize），我们可以在finalize中去拯救。

```java
public class FinalizeGC {
    public static FinalizeGC instance = null;
    public void isAlive(){
        System.out.println("I am still alive!");
    }
    @Override
    protected void finalize() throws Throwable{
        super.finalize();
        System.out.println("finalize method executed");
        FinalizeGC.instance = this;
    }
    public static void main(String[] args) throws Throwable {
        instance = new FinalizeGC();
        //对象进行第1次GC
        instance =null;
        System.gc();
        Thread.sleep(1000);//Finalizer方法优先级很低，需要等待
        if(instance !=null){
            instance.isAlive();
        }else{
            System.out.println("I am dead！");
        }
        //对象进行第2次GC
        instance =null;
        System.gc();
        Thread.sleep(1000);
        if(instance !=null){
            instance.isAlive();
        }else{
            System.out.println("I am dead！");
        }
    }
}
```

```java
finalize method executed
I am still alive!
I am dead！
```

**可以看到，对象可以被拯救一次(finalize执行第一次，但是不会执行第二次)**

代码改一下，再来一次。

```java
public class FinalizeGC {
    public static FinalizeGC instance = null;
    public void isAlive(){
        System.out.println("I am still alive!");
    }
    @Override
    protected void finalize() throws Throwable{
        super.finalize();
        System.out.println("finalize method executed");
        FinalizeGC.instance = this;
    }
    public static void main(String[] args) throws Throwable {
        instance = new FinalizeGC();
        //对象进行第1次GC
        instance =null;
        System.gc();
//        Thread.sleep(1000);//Finalizer方法优先级很低，需要等待
        if(instance !=null){
            instance.isAlive();
        }else{
            System.out.println("I am dead！");
        }
        //对象进行第2次GC
        instance =null;
        System.gc();
//        Thread.sleep(1000);
        if(instance !=null){
            instance.isAlive();
        }else{
            System.out.println("I am dead！");
        }
    }
}
```

```java
I am dead！
finalize method executed
I am dead！
```

**对象没有被拯救，这个就是finalize方法执行缓慢，还没有完成拯救，垃圾回收器就已经回收掉了。**

**所以建议大家尽量不要使用finalize，因为这个方法太不可靠。在生产中你很难控制方法的执行或者对象的调用顺序，建议大家忘了finalize方法！因为在finalize方法能做的工作，java中有更好的，比如try-finally或者其他方式可以做得更好**



## 六，各种引用

### 强引用

一般的Object obj = new Object() ，就属于强引用。在任何情况下，只有有强引用关联（与根可达）还在，垃圾回收器就永远不会回收掉被引用的对象。

### 软引用SoftReference

一些有用但是并非必需，用软引用关联的对象，系统将要发生内存溢出（OuyOfMemory）之前，这些对象就会被回收（如果这次回收后还是没有足够的空间，才会抛出内存溢出）

> 例如，一个程序用来处理用户提供的图片。如果将所有图片读入内存，这样虽然可以很快的打开图片，但内存空间使用巨大，一些使用较少的图片浪费内存空间，需要手动从内存中移除。如果每次打开图片都从磁盘文件中读取到内存再显示出来，虽然内存占用较少，但一些经常使用的图片每次打开都要访问磁盘，代价巨大。这个时候就可以用软引用构建缓存。

### 弱引用WeakReference

一些有用（程度比软引用更低）但是并非必需，用弱引用关联的对象，只能生存到下一次垃圾回收之前，GC发生时，不管内存够不够，都会被回收。

> **注意**：软引用 SoftReference和弱引用 WeakReference，可以用在内存资源紧张的情况下以及创建不是很重要的数据缓存。当系统内存不足的时候，缓存中的内容是可以被释放的。
>
> 实际运用（**WeakHashMap**、**ThreadLocal**）

### 虚引用PhantomReference

幽灵引用，最弱（随时会被回收掉）

垃圾回收的时候收到一个通知，就是为了监控垃圾回收器是否正常工作。





## 七，对象的分配策略

![对象分配原则](https://s2.loli.net/2022/05/23/cXju86rEGZ5sUeJ.png)

### 栈上分配

#### 逃逸分析

> 分析对象动态作用域，当一个对象在方法中定义后，它可能被外部方法所引用，比如：调用参数传递到其他方法中，这种称之为**方法逃逸**，甚至还有可能被外部线程访问到，例如：赋值给其他线程中访问的变量，这个称之为**线程逃逸**。

从不逃逸到方法逃逸到线程逃逸，称之为对象由低到高的不同逃逸程度。

如果确定一个对象不会逃逸出线程之外，那么让对象在**栈上分配**内存可以提高JVM的效率。

#### 逃逸分析代码

```java
/**
 * 逃逸分析-栈上分配
 * -XX:-DoEscapeAnalysis
 */
public class EscapeAnalysisTest {
    public static void main(String[] args) throws Exception {
        long start = System.currentTimeMillis();
        for (int i = 0; i < 50000000; i++) {//5千万的对象，为什么不会垃圾回收
            allocate();
        }
        System.out.println((System.currentTimeMillis() - start) + " ms");
        Thread.sleep(600000);
    }

    static void allocate() {//满足逃逸分析（不会逃逸出方法）
        MyObject myObject = new MyObject(2020, 2020.6);
    }

    static class MyObject {
        int a;
        double b;

        MyObject(int a, double b) {
            this.a = a;
            this.b = b;
        }
    }
}
```

这段代码在调用的过程中 myboject这个对象属于全局逃逸，JVM可以做栈上分配

然后通过开启和关闭DoEscapeAnalysis开关观察不同。

开启逃逸分析（JVM默认开启）

![开启逃逸分析](https://s2.loli.net/2022/05/23/sryou5lDc4QeEb6.png)

开启逃逸分析，执行效果5ms

然后关闭逃逸分析

![关闭逃逸分析](https://s2.loli.net/2022/05/23/PtA7UgrXxZboDku.png)

查看执行效果256ms

测试结果可见，开启逃逸分析对代码的执行性能有很大的影响！那为什么有这个影响？

#### 逃逸分析结论

- 如果是逃逸分析出来的对象可以在栈上分配的话，那么该对象的生命周期就跟随线程了，就不需要垃圾回收，如果是频繁的调用此方法则可以得到很大的性能提高。

- 采用了逃逸分析后，满足逃逸的对象在栈上分配

- 没有开启逃逸分析，对象都在堆上分配，会频繁触发垃圾回收（垃圾回收会影响系统性能），导致代码运行慢

### 对象优先在Eden区分配

大多数情况下，对象在新生代Eden区中分配。当Eden区没有足够空间分配时，虚拟机将发起一次Minor GC（Young GC）。

### 大对象直接进入老年代

> -Xms20m
>
> -Xmx20m
>
> -Xmn10m
>
> -XX:+PrintGCDetails
>
> -XX:PretenureSizeThreshold=4m
>
> -XX:+UseSerialGC

PretenureSizeThreshold参数只对Serial和ParNew两款收集器有效。

最典型的大对象是那种很长的字符串以及数组。这样做的目的：1.避免大量内存复制,2.避免提前进行垃圾回收，明明内存有空间进行分配。

### 长期存活的对象进入老年代

如果对象在Eden出生并经过第一次Minor GC后仍然存活，并且能被Survivor容纳的话，将被移动到Survivor空间中，并将对象年龄设为1，对象在Survivor区中每熬过一次 Minor GC，年龄就增加1，当它的年龄增加到一定程度(并发的垃圾回收器默认为15),CMS是6时，就会被晋升到老年代中。

**-XX:MaxTenuringThreshold调整**

### 对象年龄动态判定

为了能更好地适应不同程序的内存状况，虚拟机并不是永远地要求对象的年龄必须达到了MaxTenuringThreshold才能晋升老年代，如果在Survivor空间中相同年龄所有对象大小的总和大于Survivor空间的一半，年龄大于或等于该年龄的对象就可以直接进入老年代，无须等到MaxTenuringThreshold中要求的年龄

### 空间分配担保

在发生Minor GC之前，虚拟机会先检查老年代最大可用的连续空间是否大于新生代所有对象总空间，如果这个条件成立，那么Minor GC可以确保是安全的。如果不成立，则虚拟机会查看HandlePromotionFailure设置值是否允许担保失败。如果允许，那么会继续检查老年代最大可用的连续空间是否大于历次晋升到老年代对象的平均大小，如果大于，将尝试着进行一次Minor GC，尽管这次Minor GC是有风险的，如果担保失败则会进行一次Full GC；如果小于，或者HandlePromotionFailure设置不允许冒险，那这时也要改为进行一次Full GC。

### 本地线程分配缓冲(TLAB)



## 

