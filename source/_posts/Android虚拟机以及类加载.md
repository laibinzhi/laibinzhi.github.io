---
title: Android虚拟机以及类加载
date: 2022-05-24 16:30:27
tags:
  - Android
  - Java
  - JVM
---


# Android虚拟机以及类加载

## Android虚拟机

### JVM与Dalvik

- Android应用程序运行在Dalvik/ART虚拟机，并且每一个应用程序对应有一个单独的Dalvik虚拟机实例。Dalvik虚拟机实则也算是一个Java虚拟机，只不过它执行的不是class文件，而是dex文件。
- Dalvik虚拟机与Java虚拟机（JVM）共享有差不多的特性，差别在于两者执行的指令集是不一样的，前者的指令集是基于**寄存器**的，而后者的指令集是基于**堆栈**的。



### JVM基于栈的

对于基于栈的虚拟机来说，每一个运行时的线程，都有一个独立的栈。栈中记录了方法调用的历史，每有一次方法调用，栈中便会多一个**栈桢**。最顶部的栈桢称作当前栈桢，其代表着当前执行的方法。基于栈的虚拟机通过操作数栈进行所有操作。 

![JVM基于栈](https://s2.loli.net/2022/05/24/Sez4mZA1KHYJPVn.png)

<!--more-->


### Dalvik基于寄存器

**寄存器**

> 寄存器是CPU的组成部分。寄存器是有限存贮容量的高速存贮部件，它们可用来暂存指令、数据和位址。



基于寄存器的虚拟机中**没有**操作数栈，但是有很多**虚拟寄存器**。其实和操作数栈相同，这些寄存器也存放在运行时栈中，本质上就是一个数组。与JVM相似，在Dalvik VM中每个线程都有自己的PC和调用栈，方法调用的活动记录以帧为单位保存在调用栈上。



![寄存器](https://s2.loli.net/2022/05/24/mO98eCi7VcGlpnE.png)



### JVM和Dalvik的指令对比

**`int x = 4; int y = 2;` 计算 `(x + y) * (x - y)` ：**

```java
// JVM 字节码指令（基于栈）
0: iload_1	// 从局部变量1号槽位读取变量x的值到操作数栈 [4
1: iload_2	// 从局部变量2号槽位读取变量y的值到操作数栈 [4,2
2: iadd		// 栈顶两个元素相加并保存到操作数栈(x+y)   [6
3: iload_1	// 从局部变量1号槽位读取变量x的值到操作数栈 [6,4
4: iload_2	// 从局部变量2号槽位读取变量y的值到操作数栈 [6,4,2
5: isub		// 栈顶两个元素相减并保存到操作数栈(x-y)   [6,2
6: imul		// 栈顶两个元素相乘并保存到操作数栈        [12

// DVM 字节码指令（基于寄存器）
0000: add-int v0, v3, v4	// 将v3和v4寄存器的值相加并保存到v0寄存器(x+y)
0002: sub-int v1, v3, v4	// 将v3和v4寄存器的值相减并保存到v1寄存器(x-y)
0004: mul-int/2addr v0, v1	// 将v0和v1寄存器的值相乘并保存到v0寄存器

```

**与JVM版相比，可以发现Dalvik版程序的指令数明显减少了，数据移动次数也明显减少了。**



### ART与Dalvik



**DVM**也是实现了**JVM**规范的一个虚拟器，默认使用**CMS**垃圾回收器，但是与**JVM**运行 **Class** **字节码不同，DVM执行** **Dex**(Dalvik Executable Format) ——专为 Dalvik 设计的一种压缩格式。Dex 文件是很多 .class 文件处理压缩后的产物，最终可以在 Android 运行时环境执行。



而**ART**（**Android Runtime**） 是在 Android 4.4 中引入的一个开发者选项，也是 Android 5.0 及更高版本的默认Android 运行时。ART 和 Dalvik 都是运行 Dex 字节码的兼容运行时，因此针对 Dalvik 开发的应用也能在 ART 环境中运作。



#### **dexopt**

在**Dalvik**中虚拟机在加载一个dex文件时，对 dex 文件 进行 验证 和 优化的操作，其对 dex 文件的优化结果变成了 odex(Optimized dex) 文件，这个文件和 dex 文件很像，只是使用了一些优化操作码。

#### dex2oat

**ART** **预先编译机制**，在安装时对 dex 文件执行AOT 提前编译操作，编译为OAT（实际上是ELF文件）可执行文件（机器码）。



![Art](https://s2.loli.net/2022/05/24/aYHDAb3LUq1ZzXi.png)



#### Android N的运作方式

ART 使用预先 (AOT) 编译，并且从 Android N**混合使用AOT编译，解释和JIT**。

1、最初安装应用时不进行任何 AOT 编译，运行过程中**解释执行**，对经常执行的方法进行**JIT**，经过 JIT 编译的方法将会记录到**Profile**配置文件中。

2、当设备闲置和充电时，编译守护进程会运行，根据Profile文件对常用代码进行 AOT 编译。待下次运行时直接使用。

![Android N ART](https://s2.loli.net/2022/05/24/HWub69enzZDLrRP.png)

## 类加载



任何一个 Java 程序都是由一个或多个 class 文件组成，在程序运行时，需要将 class 文件加载到 JVM 中才可以使用，负责加载这些 class 文件的就是 Java 的类加载机制。ClassLoader 的作用简单来说就是加载 class 文件，提供给程序运行时使用。每个 Class 对象的内部都有一个 classLoader 字段来标识自己是由哪个 ClassLoader 加载的。

```JAVA
class Class<T> { ... private transient ClassLoader classLoader; ... }
```

ClassLoader是一个抽象类，而它的具体实现类主要有：

- BootClassLoader

  > 用于加载Android Framework层class文件。

- PathClassLoader

  > 用于Android应用程序类加载器。可以加载指定的dex，以及jar、zip、apk中的classes.dex

- DexClassLoader

  > 用于加载指定的dex，以及jar、zip、apk中的classes.dex

  ![Android ClassLoader](https://s2.loli.net/2022/05/24/DPsKq9an5Aduebc.png)

- PathClassLoader

```java
public class DexClassLoader extends BaseDexClassLoader {
    public DexClassLoader(String dexPath, String optimizedDirectory, String librarySearchPath, ClassLoader parent) {
        super(dexPath, new File(optimizedDirectory), librarySearchPath, parent);
    }
}

```

- DexClassLoader

```java
public class PathClassLoader extends BaseDexClassLoader {
    public PathClassLoader(String dexPath, ClassLoader parent) {
        super(dexPath, null, null, parent);
    }

    public PathClassLoader(String dexPath, String librarySearchPath, ClassLoader parent) {
        super(dexPath, null, librarySearchPath, parent);
    }
}
```



可以看到两者唯一的区别在于：创建 DexClassLoader 需要传递一个 optimizedDirectory 参数，并且会将其创建为 File 对象传给 super ，而 PathClassLoader 则直接给到null。因此两者都可以加载指定的**dex**，以及**jar**、**zip**、**apk**中的**classes.dex**



```java
PathClassLoader pathClassLoader = new PathClassLoader("/sdcard/xx.dex", getClassLoader());
File dexOutputDir = context.getCodeCacheDir(); 
DexClassLoader dexClassLoader = new DexClassLoader("/sdcard/xx.dex",dexOutputDir.getAbsolutePath(), null,getClassLoader());
```



其实, optimizedDirectory 参数就是**dexopt**的产出目录(odex)。那 PathClassLoader 创建时，这个目录为null，就意味着不进行dexopt？并不是， optimizedDirectory 为null时的默认路径为：**/data/dalvik-cache**。 



> 在API 26源码中，将DexClassLoader的optimizedDirectory标记为了 deprecated 弃用，实现也变为了：
>
> ......和PathClassLoader一摸一样了！
>
> ```java
> public DexClassLoader(String dexPath, String optimizedDirectory, String librarySearchPath, ClassLoader parent) { super(dexPath, null, librarySearchPath, parent); }
> ```



#### 双亲委派

**什么是双亲委派模式**？

> 某个类加载器在加载类时，首先将加载任务委托给父类加载器，依次递归，如果父类加载器可以完成类加载任务，就成功返回；只有父类加载器无法完成此加载任务或者没有父类加载器时，才自己去加载。



**为什么使用双亲委派模式？**

> 1. 避免重复加载，当父加载器已经加载了该类的时候，就没有必要子ClassLoader再加载一次。
>
> 2. 安全性考虑，防止核心API库被随意篡改。 



```java
   protected Class<?> loadClass(String name, boolean resolve)
        throws ClassNotFoundException
    {
        synchronized (getClassLoadingLock(name)) {
            // 检查class有没有被加载过
            Class<?> c = findLoadedClass(name);
            if (c == null) {
                long t0 = System.nanoTime();
                try {
                    if (parent != null) {
                        //如果parent不为null，则调用parent的loadClass进行加载
                        c = parent.loadClass(name, false);
                    } else {
                        //如果parent为null，则调用BootClassLoader进行加载
                        c = findBootstrapClassOrNull(name);
                    }
                } catch (ClassNotFoundException e) {
                    
                }

                if (c == null) {      
                    long t1 = System.nanoTime();
                  //如果都找不到，就自己查找
                    c = findClass(name);
                    sun.misc.PerfCounter.getParentDelegationTime().addTime(t1 - t0);
                    sun.misc.PerfCounter.getFindClassTime().addElapsedTimeFrom(t1);
                    sun.misc.PerfCounter.getFindClasses().increment();
                }
            }
            if (resolve) {
                resolveClass(c);
            }
            return c;
        }
    }

```



#### findClass

可以看到在所有父ClassLoader无法加载Class时，则会调用自己的 findClass 方法。 findClass 在ClassLoader中的定义为:

```java
protected Class<?> findClass(String name) throws ClassNotFoundException {
    throw new ClassNotFoundException(name);
}
```

其实任何ClassLoader子类，都可以重写 **loadClass** 与 **findClass** 。一般如果你不想使用双亲委托，则重写loadClass 修改其实现。而重写 findClass 则表示在双亲委托下，父ClassLoader都找不到Class的情况下，定义自己如何去查找一个Class。而我们的 PathClassLoader 会自己负责加载 MainActivity 这样的程序中自己编写的类，利用双亲委托父ClassLoader加载Framework中的 Activity 。说明 PathClassLoader 并没有重写loadClass ，因此我们可以来看看PathClassLoader中的 findClass 是如何实现的。

https://android.googlesource.com/platform/libcore-snapshot/+/refs/heads/ics-mr1/dalvik/src/main/java/dalvik/system/BaseDexClassLoader.java

```java
  @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
      //查找指定的class
      Class clazz = pathList.findClass(name);
        if (clazz == null) {
            throw new ClassNotFoundException(name);
        }
        return clazz;
    }
```

实现非常简单，从 pathList 中查找class。继续查看 DexPathList 

https://android.googlesource.com/platform/libcore-snapshot/+/refs/heads/ics-mr1/dalvik/src/main/java/dalvik/system/DexPathList.java



```java
 public DexPathList(ClassLoader definingContext, String dexPath,
            String libraryPath, File optimizedDirectory) {
   //.........
         // splitDexPath 实现为返回 List<File>.add(dexPath) 
         // makeDexElements 会去 List<File>.add(dexPath) 中使用DexFile加载dex文件返回 Element数组
        this.dexElements =
            makeDexElements(splitDexPath(dexPath), optimizedDirectory);
 //.........
    }
```



```java
    public Class findClass(String name) {
      //从element中获得代表Dex的 DexFile
        for (Element element : dexElements) {
            DexFile dex = element.dexFile;
            if (dex != null) {
              //查找class
                Class clazz = dex.loadClassBinaryName(name, definingContext);
                if (clazz != null) {
                    return clazz;
                }
            }
        }
        return null;
    }
```



![类加载](https://s2.loli.net/2022/05/24/8baHPVgZSflcd2i.png)



#### 热修复

PathClassLoader 中存在一个Element数组，Element类中存在一个dexFile成员表示dex文件，即：APK中有X个dex，则Element数组就有X个元素。



![热修复](https://s2.loli.net/2022/05/24/r9eHVJQk2Oaugq7.png)



在 PathClassLoader 中的Element数组为：[patch.dex , classes.dex , classes2.dex]。如果存在**Key.class**位于patch.dex与classes2.dex中都存在一份，当进行类查找时，循环获得 dexElements 中的DexFile，查找到了**Key.class**则立即返回，不会再管后续的element中的DexFile是否能加载到**Key.class**了。

因此实际上，一种热修复实现可以将出现Bug的class单独的制作一份fifix.dex文件(补丁包)，然后在程序启动时，从服务器下载fifix.dex保存到某个路径，再通过fifix.dex的文件路径，用其创建 Element 对象，然后将这个 Element 对象插入到我们程序的类加载器 PathClassLoader 的 pathList 中的 dexElements 数组头部。这样在加载出现Bug的class时会优先加载fifix.dex中的修复类，从而解决Bug。