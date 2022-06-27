---
title: 性能优化-Crash监控
date: 2022-06-28 01:15:29
tags:
  - Android
  - FrameWork
  - 性能优化
---

# 性能优化-Crash监控

Crash（应用崩溃）是由于代码异常而导致 App 非正常退出，导致应用程序无法继续使用，所有工作都停止的现象。发生 Crash 后需要重新启动应用（有些情况会自动重启），而且不管应用在开发阶段做得多么优秀，也无法避免 Crash 发生，特别是在 Android 系统中，系统碎片化严重、各 ROM 之间的差异，甚至系统Bug，都可能会导致Crash的发生。

在 Android 应用中发生的 Crash 有两种类型，Java 层的 Crash 和 Native 层 Crash。这两种Crash 的监控和获取堆栈信息有所不同。


<!--more-->



## **Java Crash**



Java的Crash监控非常简单，Java中的Thread定义了一个接口： UncaughtExceptionHandler ；用于处理未捕获的异常导致线程的终止（**注意：catch了的是捕获不到的**），当我们的应用crash的时候，就会走 UncaughtExceptionHandler.uncaughtException ，在该方法中可以获取到异常的信息，我们通

过 Thread.setDefaultUncaughtExceptionHandler 该方法来设置线程的默认异常处理器，我们可以将异常信息保存到本地或者是上传到服务器，方便我们快速的定位问题。

```java
public class CrashHandler implements Thread.UncaughtExceptionHandler{
    private static final String FILE_NAME_SUFFIX = ".trace";
    private static Thread.UncaughtExceptionHandler mDefaultCrashHandler; 
    private static Context mContext;
    
    private CrashHandler(){
    }
    
    public static void init(@NonNull Context context){ 
        //默认为：RuntimeInit#KillApplicationHandler
        mDefaultCrashHandler = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler(this); 
        mContext = context.getApplicationContext(); 
    }
    
    /**
    * 当程序中有未被捕获的异常，系统将会调用这个方法 
    * @param t 出现未捕获异常的线程 
    * @param e 得到异常信息 
    */
    @Override public void uncaughtException(Thread t, Throwable e){
        try{
            //自行处理：保存本地 
            File file = dealException(e);
            //上传服务器 
            //......
        } catch (Exception e1){ 
            e1.printStackTrace();
        } finally{ 
            //交给系统默认程序处理

            if (mDefaultCrashHandler != null){
                mDefaultCrashHandler.uncaughtException(t, e); 
            }
        }
    }
    
    /*
    ** 导出异常信息到SD卡 
    ** @param e 
    */ 
    
    private File dealException(Thread t,Throwable e) throw Exception{ 
        String time = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date());
        File f = new File(context.getExternalCacheDir().getAbsoluteFile(),"crash_info");
        if (!f.exists()) {
            f.mkdirs();
        }
        
        File crashFile = new File(f, time + FILE_NAME_SUFFIX); 
        File file = new File(PATH + File.separator + time + FILE_NAME_SUFFIX); 
        
        //往文件中写入数据 
        PrintWriter pw = new PrintWriter(new BufferedWriter(new FileWriter(file)));
        pw.println(time); 
        pw.println("Thread: "+ t.getName()); 
        pw.println(getPhoneInfo());
        e.printStackTrace(pw);//写入crash堆栈
        pw.close(); 
        return file; 
    }
    
    
    private String getPhoneInfo() throws PackageManager.NameNotFoundException{
        PackageManager pm = mContext.getPackageManager(); 
        PackageInfo pi = pm.getPackageInfo(mContext.getPackageName(), PackageManager.GET_ACTIVITIES);
        StringBuilder sb = new StringBuilder(); 
        //App版本 
        sb.append("App Version: "); 
        sb.append(pi.versionName);
        sb.append("_"); 
        sb.append(pi.versionCode + "\n"); 
        //Android版本号
        sb.append("OS Version: ");
        sb.append(Build.VERSION.RELEASE);
        sb.append("_");
        sb.append(Build.VERSION.SDK_INT + "\n");
        
        //手机制造商
        sb.append("Vendor: "); 
        sb.append(Build.MANUFACTURER + "\n"); 
        
        //手机型号 
        sb.append("Model: "); 
        sb.append(Build.MODEL + "\n");
        
        //CPU架构 
        sb.append("CPU: ");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP){ 
            sb.append(Arrays.toString(Build.SUPPORTED_ABIS)); 
        } else { 
            sb.append(Build.CPU_ABI); 
        }
        return sb.toString(); 
    }
}
```





## **NDK Crash**



### Linux信号机制

信号机制是Linux进程间通信的一种重要方式，Linux信号一方面用于正常的进程间通信和同步，另一方面它还负责监控系统异常及中断。当应用程序运行异常时，Linux内核将产生错误信号并通知当前进程。当前进程在接收到该错误信号后，可以有三种不同的处理方式。

- 忽略该信号；
- 捕捉该信号并执行对应的信号处理函数（信号处理程序）；
- 执行该信号的缺省操作（如终止进程）；

当Linux应用程序在执行时发生严重错误，一般会导致程序崩溃。其中，Linux专门提供了一类crash信号，在程序接收到此类信号时，缺省操作是将崩溃的现场信息记录到核心文件，然后终止进程。

常见崩溃信号列表：

| **信号** | **描述**                       |
| -------- | ------------------------------ |
| SIGSEGV  | 内存引用无效。                 |
| SIGBUS   | 访问内存对象的未定义部分。     |
| SIGFPE   | 算术运算错误，除以零。         |
| SIGILL   | 非法指令，如执行垃圾或特权指令 |
| SIGSYS   | 糟糕的系统调用                 |
| SIGXCPU  | 超过CPU时间限制。              |
| SIGXFSZ  | 文件大小限制。                 |

一般的出现崩溃信号，Android系统默认缺省操作是直接退出我们的程序。但是系统允许我们给某一个进程的某一个特定信号注册一个相应的处理函数（**signal**），即对该信号的默认处理动作进行修改。因此NDK Crash的监控可以采用这种信号机制，捕获崩溃信号执行我们自己的信号处理函数从而捕获NDK Crash。 



### **BreakPad**

Google breakpad是一个跨平台的崩溃转储和分析框架和工具集合，其开源地址是：https://github.com/google/breakpad。breakpad在Linux中的实现就是借助了Linux信号捕获机制实现的。因为其实现为C++，因此在Android中使用，必须借助NDK工具。