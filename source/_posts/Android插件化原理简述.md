---
title: Android插件化原理简述
date: 2018-08-17 15:18:34
tags:
  - Android
  - 安卓  
  - 插件化   
---

## 插件化技术出现背景
- #### APP体积越来越庞大，功能模块越来越多
- #### 模块耦合度高，协同开发沟通成本极大 
- #### 方法数可能查过65535，占用内存过大
<!--more-->
## 以上问题如何解决
- #### 将一个大的apk按照业务分割成多个小的apk
- #### 每个小的apk即可以独立运行又可以作为插件运行

## 插件化优势
- #### 业务模块基本完全解耦
- #### 高效并行开发（编译速度更快）
- #### 按需加载，内存占用更低等等

## 基本概念
- #### 宿主：主App,可以加载插件，也成为Host
- #### 插件：插件App,被宿主加载的App，可以是跟普通App一样的Apk文件
- #### 插件化：将一个应用按照宿主插件的方式改造就叫插件化

## 结构对比
![插件化结构对比](http://pd4brty72.bkt.clouddn.com/%E6%8F%92%E4%BB%B6%E5%8C%96%E7%BB%93%E6%9E%84%E5%AF%B9%E6%AF%94.png)

## 插件化和组件化的对比
- #### 组件化是一种编程思想（封装设计模式），而插件化是一种技术
- #### 组件化是为了代码的高度复用性而出现的
- #### 插件化是为了解决应用越来越庞大而出现的

## 插件化与动态更新（热修复）对比
- #### 与动态更新一样，都是动态加载技术的应用
- #### 动态更新是为了解决线上bug或小功能的更新而出现
- #### 插件化是为了解决应用越来越庞大而出现的

# 插件化原理
## 相关知识
1. android ClassLoader加载class文件原理
2. Java 反射原理
3. android 资源加载原理
4. 四大组件加载原理

## Manifeast处理
![Manifeast处理](http://pd4brty72.bkt.clouddn.com/Manifest%E5%A4%84%E7%90%86.jpg)
1. 构建期进行全量Merge操作
2. Bundle的依赖单独Merge,生成Bundle的Merge manifest
3. 解析各个Bundle的Merge Manifest，得到整包的BundleInfoListundleInfoList

## 插件类加载
![插件类加载](http://pd4brty72.bkt.clouddn.com/%E6%8F%92%E4%BB%B6%E7%B1%BB%E5%8A%A0%E8%BD%BD.jpg)
1. DelegateClassLoader以PatchClassLoader为父classLoader，找不到的情况下根据BundleList找到对应的BundleClassLoader
2. DelegateClassLoader的父对象为BootClassLoader，包含PathClassLoader对象，先查找当前的classLoader，再查找当前PatchClassLoader


### 如何定义ClassLoader加载类文件？如何调用插件apk文件中的类？
#### 我们通过一个简单的例子来看一下来简单模拟一下如何调用插件apk文件中的类。
1. 新建一个工程名称为*ClassLoader*,在工程里面新建一个名为Bundle的Module，Module App（代表宿主应用）和Module Bundle（代表插件应用） 两者没有任何依赖关系，我们看一下如何通过宿主应用调用我们插件应用中的类。
2. 在插件应用中创建一个类*BundleUtil*，方便我们宿主应用调用。
 
```
package com.lbz.bundle;

import android.util.Log;

public class BundleUtil {

    public static void printLog(){
        Log.i("bundle","I am a class in the bundle");
    }

}
```

3. 实现App module中的代码

```
package com.lbz.classloader;

import android.support.v7.app.AppCompatActivity;
import android.os.Bundle;

import java.io.File;
import java.lang.reflect.Method;

import dalvik.system.DexClassLoader;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        //声明一个apk path，代表我们当前插件bundle.apk存放的位置
        String apkPath = getExternalCacheDir().getAbsolutePath() + "/bundle.apk";
        //加载apk
        loadApk(apkPath);
    }

    private void loadApk(String apkPath) {
        File optDir = getDir("opt", MODE_PRIVATE);
        //创建一个DexClassLoader对象，通过它加载插件apk中class文件
        //1.apk path要加载apk文件路径
        //2.要将我们解压出来的文件放在哪里？apk是一个压缩文件，classLoader不能直接处理压缩文件，它会将apk文件解压到一个路径中，而第二个参数就是指定我们解压到哪个目录中，必须是内部目录/data
        //3.查找的关联路径，null即可
        //4.当前classLoader它的父classLoader,直接去当前classLoader即可
        DexClassLoader classLoader = new DexClassLoader(apkPath, optDir.getAbsolutePath(), null, this.getClassLoader());
        try {
            //传入插件apk中的类名获取Class字节码对象
            Class cls = classLoader.loadClass("com.lbz.bundle.BundleUtil");
            if (cls != null) {
                //通过反射创建它的实例对象
                Object instance = cls.newInstance();
                //通过反射获取它的方法
                Method method = cls.getMethod("printLog");
                //通过反射 method.invoke()调用，如果该方法 没有什么异常，他就会打印出BundleUtil中的printLog方法()
                method.invoke(instance);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

```
4. 在module Bundle 中打一个包apk文件，然后把这个包通过adb push命令上传到我们指定的文件目录中

```
$ adb push E:/zhiLearn/test/ClassLoader/bundle/build/outputs/apk/debug/bundle.apk \storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[  4%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[  8%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 13%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 17%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 22%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 26%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 30%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 35%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 39%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 44%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 48%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 52%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 57%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 61%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 66%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 70%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 74%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 79%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 83%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 88%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 92%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[ 97%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
[100%] storage/emulated/0/Android/data/com.lbz.classloader/cache/bundle.apk
E:/zhiLearn/test/ClassLoader/bundle/build/outputs/apk/debug/bundle.apk: 1 file pushed. 4.5 MB/s (1485932 bytes in 0.313s)

```

5. 运行宿主app，发现Log打印,成功表明我们的宿主调用我们的插件apk中的类，是在我们没有添加app和bundle联系的情况下通过*DexClassLoader*加载指定目录下的apk文件。
```
08-16 14:59:11.675 21886-21886/com.lbz.classloader I/bundle: I am a class in the bundle

```
#### 自定义ClassLoader

```
package com.lbz.bundle;

import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.io.InputStream;

import dalvik.system.DexClassLoader;

public class CustomClassLoader extends DexClassLoader {

    public CustomClassLoader(String dexPath, String optimizedDirectory, String librarySearchPath, ClassLoader parent) {
        super(dexPath, optimizedDirectory, librarySearchPath, parent);
    }

    /**
     * 定义了我们这个CustomClassLoader定义我们要以何种什么策略加载我们的class文件，当然我们这个demo没有什么策略，
     * 就是实现一个流程。
     */
    @Override
    protected Class<?> findClass(String name) throws ClassNotFoundException {
        byte[] classData = getClassData(name);
        if (classData != null) {
            return defineClass(name, classData, 0, classData.length);
        } else {
            throw new ClassNotFoundException();
        }
    }

    private byte[] getClassData(String name) {
        try {
            InputStream inputStream = new FileInputStream(name);
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            int bufferSize = 4096;
            byte[] buffer = new byte[bufferSize];
            int bytesNumRead = -1;
            while ((bytesNumRead = inputStream.read(buffer)) != -1) {
                baos.write(buffer, 0, bytesNumRead);
            }
            return baos.toByteArray();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }
}

```

我们这个类仅仅模拟如何定义一个自己的classLoader，并没有属于自己的策略，只是简单完成一个通过指定路径完成classes字节码的加载。以及通过获取的字节码转化成的对应class对象。

#### **是不是要为每一个插件apk都要创建一个classLoader**？
答案是肯定的。原因：
1. android系统会为每一个安装过的应用程序至少分配一个classLoader就是PathClassLoader，插件化框架是替代android系统的，所以他要为每一个插件创建一个对应classLoader。
2. 宿主或者插件类名可能同名，如果不为每一个插件单独创建一个他自己classLoader,那么路径一样的类只要在加载过一次，他就不会被加载，就会出现插件中对应的类永远不会被加载

#### **实际插件化框架开发中，类加载模块不仅仅类的查找加载，维护每一个插件的classLoader，保证每一个插件的类都能被加载到**


## 模拟插件化框架管理步骤

### 资源加载
1. 所有的Bundle Res资源都是加入到一个DelegateResources
2. Bundle Install 的时候将Res,so 等目录通过反射加入（AssetManager.addAssetPath）
3. 通过不同的packageId来区分Bundle的资源ID
4. 覆盖getIdentifier方法，兼容5.0以上系统

### 核心技术
1. 处理所有插件apk文件中的Manifest文件
2. 管理宿主apk中所有的插件apk信息
3. 为每个插件apk创建对应的类加载器，资源管理器

下面通过一个简单的类来模拟为插件apk创建对应的类加载器，资源加载器，为最核心最基本的实现。

```
package com.lbz.bundle.plugin;

import android.content.Context;
import android.content.res.AssetManager;
import android.content.res.Resources;

import java.io.File;
import java.lang.reflect.Method;
import java.util.HashMap;

import dalvik.system.DexClassLoader;

public class PluginManager {

    private static PluginManager mInstance;

    private static Context mContext;

    private static File mOptFile;

    private static HashMap<String, PluginInfo> mPluginMap;

    private PluginManager(Context context) {
        mContext = context;
        mOptFile = mContext.getDir("opt", context.MODE_PRIVATE);
        mPluginMap = new HashMap<>();
    }

    //单例模式
    public static PluginManager getInstance(Context context) {
        if (mInstance == null) {
            synchronized (PluginManager.class) {
                if (mInstance == null) {
                    mInstance = new PluginManager(context);
                }
            }
        }
        return mInstance;
    }

    private static DexClassLoader createPluginDexClassLoader(String apkPath) {
        DexClassLoader classLoader = new DexClassLoader(apkPath, mOptFile.getAbsolutePath(), null, null);
        return classLoader;
    }

    //为对应的插件创建AssetManager
    private static AssetManager createPluginAssetManager(String apkPath) {
        try {
            AssetManager assetManager = AssetManager.class.newInstance();
            Method addAssetPath = assetManager.getClass().getMethod("addAssetPath", String.class);
            addAssetPath.invoke(assetManager, apkPath);
            return assetManager;
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    //为对应的插件创建Resources
    private static Resources createPluginResources(String apkPath) {
        AssetManager assetManager = createPluginAssetManager(apkPath);
        Resources superResources = mContext.getResources();
        Resources pluginResources = new Resources(assetManager, superResources.getDisplayMetrics(), superResources.getConfiguration());
        return pluginResources;
    }

    public static PluginInfo loadApk(String apkPath) {
        if (mPluginMap.get(apkPath) != null) {
            return mPluginMap.get(apkPath);
        }
        PluginInfo pluginInfo = new PluginInfo();
        pluginInfo.mDexClassLoader = createPluginDexClassLoader(apkPath);
        pluginInfo.mAssetManager = createPluginAssetManager(apkPath);
        pluginInfo.mResources = createPluginResources(apkPath);
        mPluginMap.put(apkPath, pluginInfo);
        return pluginInfo;
    }

    static class PluginInfo {
        public DexClassLoader mDexClassLoader;
        public AssetManager mAssetManager;
        public Resources mResources;
        //
        //...
        //
    }

}

```

## 插件化框架

### 框架对比
参考Small官方比较：[COMPARISION.md](https://github.com/wequick/Small/blob/master/Android/COMPARISION.md)

为方便列表，简写如下：
```
  DyLA  : Dynamic-load-apk          @singwhatiwanna, 百度
  DiLA  : Direct-Load-apk           @FinalLody
  APF   : Android-Plugin-Framework  @limpoxe
  ACDD  : ACDD                      @bunnyblue
  DyAPK : DynamicAPK                @TediWang, 携程
  DPG   : DroidPlugin               @cmzy, 360
```

* 功能


  \\                             | DyLA   | DiLA   | ACDD   | DyAPK  | DPG    | APF    | Small
  -------------------------------|--------|--------|--------|--------|--------|--------|--------
  加载非独立插件<sup>[1]</sup>     | ×      | x      | √      | √      | ×      | √      | √
  加载.so后缀插件                  | ×      | ×      | ! <sup>[2]</sup>     | ×      | ×      | ×      | √
  Activity生命周期                | √      | √      | √      | √      | √      | √      | √
  Service动态注册                 | ×      | ×      | √      | ×      | √      | √      | x <sup>[3]</sup>
  资源分包共享<sup>[4]</sup>      | ×      | ×      | ! <sup>[5]</sup> | ! <sup>[5]</sup> | ×      | ! <sup>[6]</sup>      | √
  公共插件打包共享<sup>[7]</sup>   | ×      | ×      | ×      | ×      | ×      | ×      | √
  支持AppCompat<sup>[8]</sup>    | ×      | ×      | ×      | ×      | ×      | ×      | √
  支持本地网页组件                 | ×      | ×      | ×      | ×      | ×      | ×      | √
  支持联调插件<sup>[9]</sup>      | ×      | x      | ×      | ×      | ×      | ×      | √
  
  > [1] 独立插件：一个完整的apk包，可以独立运行。比如从你的程序跑起淘宝、QQ，但这加载起来是要闹哪样？<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;非独立插件：依赖于宿主，宿主是个壳，插件可使用其资源代码并分离之以最小化，这才是业务需要嘛。<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;-- _“所有不能加载非独立插件的插件化框架都是耍流氓”_。
  
  > [2] ACDD加载.so用了Native方法(libdexopt.so)，不是Java层，源码见[dexopt.cpp](https://github.com/bunnyblue/ACDD/blob/master/ACDDCore/jni/dexopt.cpp)。
  
  > [3] Service更新频度低，可预先注册在宿主的manifest中，如果没有很好的理由说服我，现不支持。
  
  > [4] 要实现宿主、各个插件资源可互相访问，需要对他们的资源进行分段处理以避免冲突。
  
  > [5] 这些框架修改aapt源码、重编、覆盖SDK Manager下载的aapt，我只想说_“杀(wan)鸡(de)焉(kai)用(xin)牛(jiu)刀(hao)”_。<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Small使用gradle-small-plugin，在后期修改二进制文件，实现了_**PP**_段分区。
  
  > [6] 使用public-padding对资源id的_**TT**_段进行分区，分开了宿主和插件。但是插件之间无法分段。
  
  > [7] 除了宿主提供一些公共资源与代码外，我们仍需封装一些业务层面的公共库，这些库被其他插件所依赖。<br/>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;公共插件打包的目的就是可以单独更新公共库插件，并且相关插件不需要动到。
  
  > [8] AppCompat: Android Studio默认添加的主题包，Google主推的Metrial Design包也依赖于此。大势所趋。
  
  > [9] 联调插件：使用Android Studio调试![🐞][as-debug]宿主时，可直接在插件代码中添加断点调试。
  
* 透明度

|  | ACDD | DyAPK |APF |Small |
| :------:| :------: | :------: |:------: |:------: |
| 插件Activity代码无需修改	 | √  | √  |√  |√  |
| 插件引用外部资源无需修改name     | × | × |× |√ |
| 插件模块无需修改build.gradle	 | × | × |× |√ |



如何选择？

**只有Small和Atlas更新比较频繁，其余的基本超过一年两年没有更新了，不建议再使用，small对比于atlas较为简单，容易集成，建议使用[small](https://github.com/wequick/Small)**




