---
title: Android Framework之PKMS
date: 2022-06-28 00:59:23
tags:
  - Android
  - FrameWork
  - 源码
---


# Android Framework之PKMS

## 一，定义

**PackageManagerService**（简称 PKMS），是 Android 系统中核心服务之一，负责应用程序的**安装**，**卸载**，**信息查询**等工作。

- Android系统启动时，会启动（应用程序管理服务器PKMS），此服务负责扫描系统中特定的目录，寻找里面的APK格式的文件，并对这些文件进行解析，然后得到应用程序相关信息，最后完成应用程序的安装
- PKMS在安装应用过程中, 会全面解析应用程序的AndroidManifest.xml文件, 来得到Activity,Service, BroadcastReceiver, ContextProvider等信息,在结合PKMS服务就可以在OS中正常的使用应用程序了
- 在Android系统中, 系统启动时由SystemServer启动PKMS服务,启动该服务后会执行应用程序的安装过程

> 1.解析AndroidNanifest.xml清单文件，解析清单文件中的所有节点信息
>
> 2.扫描.apk文件，安装系统应用，安装本地应用等
>
> 3.管理本地应用，主要有， 安装，卸载，应用信息查询 等


<!--more-->




## 二，PKMS常用到的类

![微信图片_20220606220024](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/a6f9d75fcfda4910b90ed1b5c11da33a~tplv-k3u1fbpfcp-zoom-1.image)

客户端可通过Context.getPackageManager()获得ApplicationPackageManager对象, 而mPM指向的是Proxy代理，当调用到mPM.方法后，将会调用到IPackageManager的Proxy代理方法，然后通过Binder机制中的mRemote与服务端PackageManagerService通信 并调用到PackageManagerService的方法





## 三，PKMS启动流程

![微信图片_20220606220145](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/f70164a53b9d4d00b0a4c5381a2a6079~tplv-k3u1fbpfcp-zoom-1.image)

SystemServer启动PKMS： 先是在SystemServer.startBootstrapServices()函数中启动PKMS服务，再调用startOtherServices()函数中对dex优化，磁盘管理功能，让PKMS进入systemReady状态。



![微信图片_20220606220622](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/573c20595d7d443b946406c2ae742e9d~tplv-k3u1fbpfcp-zoom-1.image)



- **startBootstrapServices**。()首先启动Installer服务，也就是安装器，随后判断当前的设备是否处于加密状态，如果是则只是解析核心应用，接着调用PackageManagerService的静态方法main来创建pms对象

  > 1.  启动Installer服务
  > 2. 获取设备是否加密(手机设置密码)，如果设备加密了，则只解析"core"应用
  > 3. 调用PKMS main方法初始化PackageManagerService，其中调用PackageManagerService()构造函数创建了PKMS对象
  > 4. 如果设备没有加密，操作它。管理A/B OTA dexopting。 

  ```java
  private void startBootstrapServices() { 
      ... 
          // 第一步：启动Installer 
          // 阻塞等待installd完成启动，以便有机会创建具有适当权限的关键目录，如/data/user。 
          // 我们需要在初始化其他服务之前完成此任务。 
          Installer installer = mSystemServiceManager.startService(Installer.class);
          mActivityManagerService.setInstaller(installer);
      
      ... 
          // 第二步：获取设别是否加密(手机设置密码)，如果设备加密了，则只解析"core"应用，mOnlyCore = true，后面会频繁使用该变量进行条件判断 
          String cryptState = VoldProperties.decrypt().orElse("");
          if (ENCRYPTING_STATE.equals(cryptState)) {
              Slog.w(TAG, "Detected encryption in progress - only parsing core apps");
              mOnlyCore = true;
          } else if (ENCRYPTED_STATE.equals(cryptState)) {
              Slog.w(TAG, "Device encrypted - only parsing core apps");
              mOnlyCore = true;
          }
          // 第三步：调用main方法初始化PackageManagerService 
          mPackageManagerService = PackageManagerService.main(mSystemContext, installer, mFactoryTestMode != FactoryTest.FACTORY_TEST_OFF, mOnlyCore);
          // PKMS是否是第一次启动
          mFirstBoot = mPackageManagerService.isFirstBoot(); 
          // 第四步：如果设备没有加密，操作它。管理A/B OTA dexopting。 
          if (!mOnlyCore) { 
              boolean disableOtaDexopt = SystemProperties.getBoolean("config.disable_otadexopt", false); 
              OtaDexoptService.main(mSystemContext, mPackageManagerService); 
          }
      ... 
  }
  ```

  

- **startOtherServices**

  > 5.  updatePackagesIfNeeded ，完成dex优化；
  > 6. 执行 performFstrimIfNeeded ，完成磁盘维护；
  > 7. 调用systemReady，准备就绪。

```java
private void startOtherServices() { 
    ...
        if (!mOnlyCore) { 
            ... 
                // 第五步：如果设备没有加密，执行performDexOptUpgrade，完成dex优化；
                mPackageManagerService.updatePackagesIfNeeded(); 
        }
    ... 
            // 第六步：最终执行performFstrim，完成磁盘维护 
            mPackageManagerService.performFstrimIfNeeded(); 
    ... 
        // 第七步：PKMS准备就绪
        mPackageManagerService.systemReady();
    ...
}
```





## 四，PKMS main

#### PKMS main方法概述

**main函数主要工作：**

> 1. 检查Package编译相关系统属性
> 2.  调用PackageManagerService构造方法
> 3. 启用部分应用服务于多用户场景
> 4.  往ServiceManager中注册”package”和”package_native”。 

```java
public static PackageManagerService main(Context context, Installer installer, boolean factoryTest, boolean onlyCore) { 
    // (1)检查Package编译相关系统属性 
    PackageManagerServiceCompilerMapping.checkProperties(); 
    //(2)调用PackageManagerService构造方法,参考【PKMS构造方法】
    PackageManagerService m = new PackageManagerService(context, installer, factoryTest, onlyCore); 
    //(3)启用部分应用服务于多用户场景 
    m.enableSystemUserPackages(); 
    //(4)往ServiceManager中注册”package”和”package_native”。 
    ServiceManager.addService("package", m);
    final PackageManagerNative pmn = m.new PackageManagerNative();
    ServiceManager.addService("package_native", pmn);
    return m;
}
```



#### PKMS构造方法详解

![微信图片_20220606222353](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/80eef75c5e194f4eb9f1a7b399a8e343~tplv-k3u1fbpfcp-zoom-1.image)

**PKMS的构造函数中由两个重要的锁和5个阶段构成**

> 两个重要的锁(mInstallLock、mPackages): 
>
> - mInstallLock ：用来保护所有安装apk的访问权限，此操作通常涉及繁重的磁盘数据读写等操作，并 且是单线程操作，故有时候会处理很慢, 此锁不会在已经持有mPackages锁的情况下火的，反之，在已经持有mInstallLock锁的情况下，立即 获取mPackages是安全的 
>
> - mPackages：用来解析内存中所有apk的package信息及相关状态。 



> 5个阶段
>
> - 阶段1：BOOT_PROGRESS_PMS_START 
>
> - 阶段2：BOOT_PROGRESS_PMS_SYSTEM_SCAN_START 
>
> - 阶段3：BOOT_PROGRESS_PMS_DATA_SCAN_START 
>
> - 阶段4：BOOT_PROGRESS_PMS_SCAN_END 
>
> - 阶段5：BOOT_PROGRESS_PMS_READY



```java
//构造函数
public PackageManagerService(Context context, Installer installer, boolean factoryTest, boolean onlyCore) { 
    ...
     // 阶段1：BOOT_PROGRESS_PMS_START 
     EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_START, SystemClock.uptimeMillis()); 
     // 阶段2：BOOT_PROGRESS_PMS_SYSTEM_SCAN_START 
     EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_SYSTEM_SCAN_START, startTime);
    ...
     // 阶段3：BOOT_PROGRESS_PMS_DATA_SCAN_STAR 
     if (!mOnlyCore) { 
         EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_DATA_SCAN_START, SystemClock.uptimeMillis()); 
     }
    ... 
     // 阶段4：BOOT_PROGRESS_PMS_SCAN_END 
     EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_SCAN_END, SystemClock.uptimeMillis()); 
    ... 
     // 阶段5：BOOT_PROGRESS_PMS_READY 
     EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_READY, SystemClock.uptimeMillis()); 
}
```





##### 阶段1-BOOT_PROGRESS_PMS_START

1. 构造 DisplayMetrics ，保存分辨率等相关信息；
2. 创建Installer对象，与installd交互；
3. 创建mPermissionManager对象，进行权限管理；
4. 构造Settings类，保存安装包信息，清除路径不存在的孤立应用，主要涉及/data/system/目录的packages.xml，packages-backup.xml，packages.list，packages-stopped.xml，packages-stopped，backup.xml等文件。
5. 构造PackageDexOptimizer及DexManager类，处理dex优化；
6. 创建SystemConfig实例，获取系统配置信息，配置共享lib库；
7. 创建PackageManager的handler线程，循环处理外部安装相关消息。



```java
public PackageManagerService(...) {
    LockGuard.installLock(mPackages, LockGuard.INDEX_PACKAGES);
    EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_START, SystemClock.uptimeMillis());
    mContext = context; mFactoryTest = factoryTest; // 一般为false，即非工厂生产模式 
    mOnlyCore = onlyCore; //标记是否只加载核心服务 
    // 【注意】(1) 构造 DisplayMetrics ，保存分辨率等相关信息； 
    mMetrics = new DisplayMetrics(); // 分辨率配置 
    // 【注意】(2)创建Installer对象，与installd交互； 
    mInstaller = installer; //保存installer对象
    //创建提供服务/数据的子组件。这里的顺序很重要,使用到了两个重要的同步锁：mInstallLock、 mPackages 
    synchronized (mInstallLock) {
        synchronized (mPackages) { 
            // 公开系统组件使用的私有服务
            // 本地服务 
            LocalServices.addService(PackageManagerInternal.class, new PackageManagerInternalImpl()); 
            // 多用户管理服务 
            sUserManager = new UserManagerService(context, this, new UserDataPreparer(mInstaller,mInstallLock,mContext,mOnlyCore), mPackages); mComponentResolver = new ComponentResolver(sUserManager, LocalServices.getService(PackageManagerInternal.class), mPackages);
            // 【注意】 (3)创建mPermissionManager对象，进行权限管理； 
            // 权限管理服务
            mPermissionManager = PermissionManagerService.create(context, mPackages /*externalLock*/); 
            mDefaultPermissionPolicy = mPermissionManager.getDefaultPermissionGrantPolicy(); 
            //创建Settings对象 
            mSettings = new Settings(Environment.getDataDirectory(), mPermissionManager.getPermissionSettings(), mPackages); 
        }
    }
    // 【注意】(4)构造Settings类，保存安装包信息，清除路径不存在的孤立应用，主要涉 及/data/system/目录的packages.xml，packages-backup.xml， packages.list， packages-stopped.xml，packages-stopped-backup.xml等文件。 
    // 添加system, phone, log, nfc, bluetooth, shell，se，networkstack 这8种 shareUserId到mSettings； 
    mSettings.addSharedUserLPw("android.uid.system", Process.SYSTEM_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED); 
    mSettings.addSharedUserLPw("android.uid.phone", RADIO_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED); 
    mSettings.addSharedUserLPw("android.uid.log", LOG_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED);
    mSettings.addSharedUserLPw("android.uid.nfc", NFC_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED);
    mSettings.addSharedUserLPw("android.uid.bluetooth", BLUETOOTH_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED);
    mSettings.addSharedUserLPw("android.uid.shell", SHELL_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED);
    mSettings.addSharedUserLPw("android.uid.se", SE_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED); mSettings.addSharedUserLPw("android.uid.networkstack", NETWORKSTACK_UID, ApplicationInfo.FLAG_SYSTEM, ApplicationInfo.PRIVATE_FLAG_PRIVILEGED);
    ... 
        // 【注意】(5)构造PackageDexOptimizer及DexManager类，处理dex优化； 
        // DexOpt优化
        mPackageDexOptimizer = new PackageDexOptimizer(installer, mInstallLock, context,
"*dexopt*"); 
    mDexManager = new DexManager(mContext, this, mPackageDexOptimizer, installer, mInstallLock); 
    // ART虚拟机管理服务
    mArtManagerService = new ArtManagerService(mContext, this, installer, mInstallLock);
    mMoveCallbacks = new MoveCallbacks(FgThread.get().getLooper());
    mViewCompiler = new ViewCompiler(mInstallLock, mInstaller); 
    // 权限变化监听器
    mOnPermissionChangeListeners = new OnPermissionChangeListeners( FgThread.get().getLooper()); 
    mProtectedPackages = new ProtectedPackages(mContext);
    mApexManager = new ApexManager(context); 
    // 获取默认分辨率 getDefaultDisplayMetrics(context, mMetrics); 
    // 【注意】(6)创建SystemConfig实例，获取系统配置信息，配置共享lib库；
    //拿到SystemConfig()的对象，其中会调用SystemConfig的readPermissions()完成权限的读取 
    SystemConfig systemConfig = SystemConfig.getInstance();
    synchronized (mInstallLock) {
        // writer
        synchronized (mPackages) { 
            // 【注意】(7)创建PackageManager的handler线程，循环处理外部安装相 关消息。
            // 启动"PackageManager"线程，负责apk的安装、卸载 
            mHandlerThread = new ServiceThread(TAG, Process.THREAD_PRIORITY_BACKGROUND, true /*allowIo*/); 
            mHandlerThread.start(); 
            // 应用handler 
            mHandler = new PackageHandler(mHandlerThread.getLooper());
            // 进程记录handler 
            mProcessLoggingHandler = new ProcessLoggingHandler(); 
            // Watchdog监听ServiceThread是否超时：10分钟 
            Watchdog.getInstance().addThread(mHandler, WATCHDOG_TIMEOUT);
            // Instant应用注册
            mInstantAppRegistry = new InstantAppRegistry(this);
            // 共享lib库配置 
            ArrayMap<String, SystemConfig.SharedLibraryEntry> libConfig = systemConfig.getSharedLibraries(); final int 
                builtInLibCount = libConfig.size();
            for (int i = 0; i < builtInLibCount; i++) { 
                String name = libConfig.keyAt(i); 
                SystemConfig.SharedLibraryEntry entry = libConfig.valueAt(i);
                addBuiltInSharedLibraryLocked(entry.filename, name);
            }
            ... 
                // 读取安装相关SELinux策略
                SELinuxMMAC.readInstallPolicy(); 
            // 返回栈加载
            FallbackCategoryProvider.loadFallbacks(); 
             //读取并解析/data/system下的XML文件
            mFirstBoot = !mSettings.readLPw(sUserManager.getUsers(false));

            // 清理代码路径不存在的孤立软件包
            final int packageSettingCount = mSettings.mPackages.size();
            for (int i = packageSettingCount - 1; i >= 0; i--) { 
                PackageSetting ps = mSettings.mPackages.valueAt(i); 
                if (!isExternal(ps) && (ps.codePath == null || !ps.codePath.exists()) && 
                    mSettings.getDisabledSystemPkgLPr(ps.name) != null) { 
                    mSettings.mPackages.removeAt(i); 
                    mSettings.enableSystemPackageLPw(ps.name); 
                }
            }
            // 如果不是首次启动，也不是CORE应用，则拷贝预编译的DEX文件
            if (!mOnlyCore && mFirstBoot) { 
                requestCopyPreoptedFiles(); 
            }

            ...
        } 
        // synchronized (mPackages) 
    }
    
}
```

此readLPw 是上面调下来的哦：

**mSettings.readLPw**

```java
readLPw()会扫描下面5个文件
    1) "/data/system/packages.xml" 所有安装app信息
    2) "/data/system/packages-backup.xml" 所有安装app信息之备份的信息记录
    3) "/data/system/packages.list" 所有安装app信息 
    4) "/data/system/packages-stopped.xml" 所有强制停止app信息 
    5) "/data/system/packages-stopped-backup.xml" 所有强制停止app信息之备份的信息记录
    
    个文件共分为三组，简单的作用描述如下：
    packages.xml：PKMS 扫描完目标文件夹后会创建该文件。当系统进行程序安装、卸载和更新等操作时，均 会更新该文件。该文件保存了系统中与 package 相关的一些信息。
    packages.list：描述系统中存在的所有非系统自带的 APK 的信息。当这些程序有变动时，PKMS 就会更 新该文件。
    packages-stopped.xml：从系统自带的设置程序中进入应用程序页面，然后在选择强制停止 （ForceStop）某个应用时，系统会将该应用的相关信息记录到此文件中。也就是该文件保存系统中被用户强 制停止的 Package 的信息。 
    
    这些目录的指向，都在Settings中的构造函数完成， 如下所示，得到目录后调用readLPw()进行扫描 
    // 先看Settings构造函数 
    Settings(File dataDir, PermissionSettings permission, Object lock) {
    mLock = lock;
    mPermissions = permission; 
    mRuntimePermissionsPersistence = new RuntimePermissionPersistence(mLock); 
    mSystemDir = new File(dataDir, "system"); //mSystemDir指向目录"/data/system" 
    mSystemDir.mkdirs(); //创建 "/data/system" 
    //设置权限
    FileUtils.setPermissions(mSystemDir.toString(), FileUtils.S_IRWXU|FileUtils.S_IRWXG
                             |FileUtils.S_IROTH|FileUtils.S_IXOTH, -1, -1); 
    //(1)指向目录"/data/system/packages.xml"
    mSettingsFilename = new File(mSystemDir, "packages.xml"); 
    //(2)指向目录"/data/system/packages-backup.xml" 
    mBackupSettingsFilename = new File(mSystemDir, "packages-backup.xml"); 
    //(3)指向目录"/data/system/packages.list"
    mPackageListFilename = new File(mSystemDir, "packages.list"); 
    FileUtils.setPermissions(mPackageListFilename, 0640, SYSTEM_UID, PACKAGE_INFO_GID); 
    //(4)指向目录"/data/system/packages-stopped.xml"
    mStoppedPackagesFilename = new File(mSystemDir, "packages-stopped.xml"); 
    //(5)指向目录"/data/system/packages-stopped-backup.xml"
    mBackupStoppedPackagesFilename = new File(mSystemDir, "packages-stopped- backup.xml"); 
}
    // 再看readLPw函数
[Settings.java]
boolean readLPw(@NonNull List<UserInfo> users) { 
    FileInputStream str = null;
    ... 
        if (str == null) {
            str = new FileInputStream(mSettingsFilename); 
        }
    //解析"/data/system/packages.xml" 
    XmlPullParser parser = Xml.newPullParser();
    parser.setInput(str, StandardCharsets.UTF_8.name()); 
    int type;
    while ((type = parser.next()) != XmlPullParser.START_TAG && type != XmlPullParser.END_DOCUMENT) { ; }int outerDepth = parser.getDepth(); 
    while ((type = parser.next()) != XmlPullParser.END_DOCUMENT && (type != XmlPullParser.END_TAG || parser.getDepth() > outerDepth)) { 
        if (type == XmlPullParser.END_TAG || type == XmlPullParser.TEXT) {
            continue;
        }
        //根据XML的各个节点进行各种操作，例如读取权限、shared-user等 
        String tagName = parser.getName();
        if (tagName.equals("package")) {
            readPackageLPw(parser);
        } else if (tagName.equals("permissions")) { 
            mPermissions.readPermissions(parser); 
        } else if (tagName.equals("permission-trees")) {
            mPermissions.readPermissionTrees(parser);
        } else if (tagName.equals("shared-user")) {
            readSharedUserLPw(parser);
        }... 
    }
    str.close(); 
    ... 
        return true;
}
```



##### 阶段2-BOOT_PROGRESS_PMS_SYSTEM_SCAN_START

1.  从init.rc中获取环境变量BOOTCLASSPATH和SYSTEMSERVERCLASSPATH；
2. 对于旧版本升级的情况，将安装时获取权限变更为运行时申请权限；
3. 扫描system/vendor/product/odm/oem等目录的priv-app、app、overlay包；
4. 清除安装时临时文件以及其他不必要的信息。

```java
public PackageManagerService(Context context, Installer installer, boolean factoryTest, boolean onlyCore) { 
    synchronized (mInstallLock) {
        synchronized (mPackages) { 
            // 记录扫描开始时间 
            long startTime = SystemClock.uptimeMillis();
            EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_SYSTEM_SCAN_START, startTime); 
            // 【注意】 (1)从init.rc中获取环境变量BOOTCLASSPATH和 SYSTEMSERVERCLASSPATH；
            
            //获取环境变量，init.rc 
            final String bootClassPath = System.getenv("BOOTCLASSPATH"); 
            final String systemServerClassPath = System.getenv("SYSTEMSERVERCLASSPATH"); 
            ... 
                
            // 获取system/framework目录
             File frameworkDir = new File(Environment.getRootDirectory(), "framework");
            // 获取内部版本
            final VersionInfo ver = mSettings.getInternalVersion(); 
            // 判断fingerprint是否有更新
            mIsUpgrade = !Build.FINGERPRINT.equals(ver.fingerprint); 
            ... 
                // 【注意】 (2)对于旧版本升级的情况，将安装时获取权限变更为运行时申请权限； 
                // 对于Android M之前版本升级上来的情况，需将系统应用程序权限从安装升级到运行时 
                mPromoteSystemApps = mIsUpgrade && ver.sdkVersion <= Build.VERSION_CODES.LOLLIPOP_MR1; 
            // 对于Android N之前版本升级上来的情况，需像首次启动一样处理package 
            mIsPreNUpgrade = mIsUpgrade && ver.sdkVersion < Build.VERSION_CODES.N;
            mIsPreNMR1Upgrade = mIsUpgrade && ver.sdkVersion < Build.VERSION_CODES.N_MR1; 
            mIsPreQUpgrade = mIsUpgrade && ver.sdkVersion < Build.VERSION_CODES.Q; 
            // 在扫描之前保存预先存在的系统package的名称，不希望自动为新系统应用授予运行时权限
            if (mPromoteSystemApps) {
                Iterator<PackageSetting> pkgSettingIter = mSettings.mPackages.values().iterator();
                while (pkgSettingIter.hasNext()) {
                    PackageSetting ps = pkgSettingIter.next();
                    if (isSystemApp(ps)) {

                        mExistingSystemPackages.add(ps.name);
                    }
                }
            }
            // 准备解析package的缓存
            mCacheDir = preparePackageParserCache(); 
            // 设置flag，而不在扫描安装时更改文件路径
            int scanFlags = SCAN_BOOTING | SCAN_INITIAL;
            ...
                // 【注意：】(3)扫描system/vendor/product/odm/oem等目录的priv-app、 app、overlay包；
                //扫描以下路径： /vendor/overlay、/product/overlay、/product_services/overlay、/odm/overlay、/oem/ overlay、/system/framework /system/priv-app、/system/app、/vendor/priv- app、/vendor/app、/odm/priv-app、/odm/app、/oem/app、/oem/priv-app、 /product/priv-app、/product/app、/product_services/priv- app、/product_services/app、/product_services/priv-app
                // [ PMSapk的安装]
                scanDirTracedLI(new File(VENDOR_OVERLAY_DIR),...); 
            scanDirTracedLI(new File(PRODUCT_OVERLAY_DIR),...); 
            scanDirTracedLI(new File(PRODUCT_SERVICES_OVERLAY_DIR),...); 
            scanDirTracedLI(new File(ODM_OVERLAY_DIR),...);
            scanDirTracedLI(new File(OEM_OVERLAY_DIR),...); 
            ... 
                
                final List<String> possiblyDeletedUpdatedSystemApps = new ArrayList<>();
            
            final List<String> stubSystemApps = new ArrayList<>();
            // 删掉不存在的package 
            if (!mOnlyCore) {
                final Iterator<PackageParser.Package> pkgIterator = mPackages.values().iterator();
                while (pkgIterator.hasNext()) { 
                    final PackageParser.Package pkg = pkgIterator.next(); 
                    if (pkg.isStub) { 
                        stubSystemApps.add(pkg.packageName); 
                    } 
                }
                final Iterator<PackageSetting> psit = mSettings.mPackages.values().iterator(); 
                while (psit.hasNext()) { 
                    PackageSetting ps = psit.next();
                    // 如果不是系统应用，则不被允许disable 
                    if ((ps.pkgFlags & ApplicationInfo.FLAG_SYSTEM) == 0) {
                        continue;
                    }
                    // 如果应用被扫描，则不允许被擦除
                    final PackageParser.Package scannedPkg = mPackages.get(ps.name); if (scannedPkg != null) { // 如果系统应用被扫描且存在disable应用列表中，则只能通过OTA升级添加
                        if (mSettings.isDisabledSystemPackageLPr(ps.name)) {
                            ... 
                                removePackageLI(scannedPkg, true);
                            
                            mExpectingBetter.put(ps.name, ps.codePath); 
                        }continue;
                    }
                    ...
                }
            }
            // 【注意】(4)清除安装时临时文件以及其他不必要的信息。
            // 删除临时文件
            deleteTempPackageFiles(); 
            // 删除没有关联应用的共享UID标识 
            mSettings.pruneSharedUsersLPw(); 
            ... 
        }
        ...
    }
    ... 
}
```



##### 阶段3-BOOT_PROGRESS_PMS_DATA_SCAN_START

对于不仅仅解析核心应用的情况下，还处理data目录的应用信息，及时更新，祛除不必要的数据。

```java
public PackageManagerService(Context context, Installer installer, boolean factoryTest, boolean onlyCore) {
    synchronized (mInstallLock) {
        synchronized (mPackages) {
            ...
                if (!mOnlyCore) { 
                    EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_DATA_SCAN_START, SystemClock.uptimeMillis()); 
                    scanDirTracedLI(sAppInstallDir, 0, scanFlags | SCAN_REQUIRE_KNOWN, 0);
                    ...
                        // 移除通过OTA删除的更新系统应用程序的禁用package设置 
                        // 如果更新不再存在，则完全删除该应用。否则，撤消其系统权限 
                        for (int i = possiblyDeletedUpdatedSystemApps.size() - 1; i >= 0; --i) {
                            final String packageName = possiblyDeletedUpdatedSystemApps.get(i); 
                            final PackageParser.Package pkg = mPackages.get(packageName);
                            final String msg;
                            mSettings.removeDisabledSystemPackageLPw(packageName);
                            ... 
                        }
                    // 确保期望在userdata分区上显示的所有系统应用程序实际显示 
                    // 如果从未出现过，需要回滚以恢复系统版本
                    for (int i = 0; i < mExpectingBetter.size(); i++) { 
                        final String packageName = mExpectingBetter.keyAt(i); 
                        if (!mPackages.containsKey(packageName)) {
                            final File scanFile = mExpectingBetter.valueAt(i); 
                            ... 
                                
                                mSettings.enableSystemPackageLPw(packageName);

                            try {
                                //扫描APK
                                scanPackageTracedLI(scanFile, reparseFlags, rescanFlags, 0, null);
                            } catch (PackageManagerException e) { 
                                Slog.e(TAG, "Failed to parse original system package: " + e.getMessage());
                            } 
                        } 
                    }
                    // 解压缩并安装任何存根系统应用程序。必须最后执行此操作以确保替换或禁用所有存根 
                    installSystemStubPackages(stubSystemApps, scanFlags);
                    ...
                        // 获取storage manager包名
                        mStorageManagerPackage = getStorageManagerPackageName(); 
                    // 解决受保护的action过滤器。只允许setup wizard（开机向导）为这些action 设置高优先级过滤器
                    mSetupWizardPackage = getSetupWizardPackageName(); 
                    ...
                        // 更新客户端以确保持有正确的共享库路径
                        updateAllSharedLibrariesLocked(null, Collections.unmodifiableMap(mPackages)); 
                    ...
                        // 读取并更新要保留的package的上次使用时间 
                        mPackageUsage.read(mPackages);
                    mCompilerStats.read();
                }
        }
    }
}
```





##### 阶段4-BOOT_PROGRESS_PMS_SCAN_END

1.  sdk版本变更，更新权限；
2. OTA升级后首次启动，清除不必要的缓存数据；
3. 权限等默认项更新完后，清理相关数据；
4. 更新packag

```java
public PackageManagerService(Context context, Installer installer, boolean factoryTest, boolean onlyCore) { 
    synchronized (mInstallLock) { 
        synchronized (mPackages) { 
            ... 
                EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_SCAN_END, SystemClock.uptimeMillis()); 
            // 【注意】 (1) sdk版本变更，更新权限；
            // 如果自上次启动以来，平台SDK已改变，则需要重新授予应用程序权限以捕获出现的任何 新权限
            final boolean sdkUpdated = (ver.sdkVersion != mSdkVersion);
            mPermissionManager.updateAllPermissions(
                StorageManager.UUID_PRIVATE_INTERNAL, sdkUpdated, mPackages.values(), mPermissionCallback);
            ...
                // 如果这是第一次启动或来自Android M之前的版本的升级，并且它是正常启动，那需要在 所有已定义的用户中初始化默认的首选应用程序 
                if (!onlyCore && (mPromoteSystemApps || mFirstBoot)) { 
                    for (UserInfo user : sUserManager.getUsers(true)) {
                        mSettings.applyDefaultPreferredAppsLPw(user.id);
                        primeDomainVerificationsLPw(user.id);
                    }
                }
            // 在启动期间确实为系统用户准备存储，因为像SettingsProvider和SystemUI这样的核 心系统应用程序无法等待用户启动 
            final int storageFlags;
            if (StorageManager.isFileEncryptedNativeOrEmulated()) {
                storageFlags = StorageManager.FLAG_STORAGE_DE;
            } else {
                storageFlags = StorageManager.FLAG_STORAGE_DE | StorageManager.FLAG_STORAGE_CE; 
            }
            ... 
                // 【注意】(2) OTA升级后首次启动，清除不必要的缓存数据；
                // 如果是在OTA之后首次启动，并且正常启动，那需要清除代码缓存目录，但不清除应用程 序配置文件
                if (mIsUpgrade && !onlyCore) { 
                    Slog.i(TAG, "Build fingerprint changed; clearing code caches");
                    for (int i = 0; i < mSettings.mPackages.size(); i++) {
                        final PackageSetting ps = mSettings.mPackages.valueAt(i); 
                        if (Objects.equals(StorageManager.UUID_PRIVATE_INTERNAL, ps.volumeUuid)) { 
                            // No apps are running this early, so no need to freeze 
                            clearAppDataLIF(ps.pkg, UserHandle.USER_ALL, FLAG_STORAGE_DE | FLAG_STORAGE_CE | 
                                            FLAG_STORAGE_EXTERNAL | Installer.FLAG_CLEAR_CODE_CACHE_ONLY);
                        }
                    }
                    ver.fingerprint = Build.FINGERPRINT; 
                }
            //安装Android-Q前的非系统应用程序在Launcher中隐藏他们的图标 
            if (!onlyCore && mIsPreQUpgrade) {
                Slog.i(TAG, "Whitelisting all existing apps to hide their icons"); 
                int size = mSettings.mPackages.size();
                for (int i = 0; i < size; i++) {
                    final PackageSetting ps = mSettings.mPackages.valueAt(i); 
                    if ((ps.pkgFlags & ApplicationInfo.FLAG_SYSTEM) != 0) {
                        continue; 
                    }
                    ps.disableComponentLPw(PackageManager.APP_DETAILS_ACTIVITY_CLASS_NAME, UserHandle.USER_SYSTEM);
                }
            }
            // 【注意】 (3) 权限等默认项更新完后，清理相关数据；

            // 仅在权限或其它默认配置更新后清除 
            mExistingSystemPackages.clear();
            mPromoteSystemApps = false;
            ...
                // 所有变更均在扫描过程中完成
                ver.databaseVersion = Settings.CURRENT_DATABASE_VERSION;
            // 【注意】(4) 更新package.xml //降级去读取
            mSettings.writeLPr(); 
        }
    } 
}
```



##### 阶段5-BOOT_PROGRESS_PMS_READY

GC回收内存 和一些细节而已

```java
public PackageManagerService(Context context, Installer installer, boolean factoryTest, boolean onlyCore) {
    synchronized (mInstallLock) { 
        synchronized (mPackages) { 
            ...
                EventLog.writeEvent(EventLogTags.BOOT_PROGRESS_PMS_READY, SystemClock.uptimeMillis());
            ... 
                //PermissionController 主持 缺陷许可证的授予和角色管理，所以这是核心系统的一个 关键部分。 
                mRequiredPermissionControllerPackage = getRequiredPermissionControllerLPr();
            ... 
                updateInstantAppInstallerLocked(null);
            // 阅读并更新dex文件的用法
            // 在PM init结束时执行此操作，以便所有程序包都已协调其数据目录 
            // 此时知道了包的代码路径，因此可以验证磁盘文件并构建内部缓存 
            // 使用文件预计很小，因此与其他活动（例如包扫描）相比，加载和验证它应该花费相当小 的时间 
            final Map<Integer, List<PackageInfo>> userPackages = new HashMap<> ();
            for (int userId : userIds) { 
                userPackages.put(userId, getInstalledPackages(/*flags*/ 0, userId).getList());
            }mDexManager.load(userPackages); 
            if (mIsUpgrade) {
                MetricsLogger.histogram(null, "ota_package_manager_init_time", (int) (SystemClock.uptimeMillis() - startTime)); 
            }
        }
    }
    ... 
        // 【注意】GC回收内存
        // 打开应用之后，及时回收处理 
        Runtime.getRuntime().gc();
    // 上面的初始扫描在持有mPackage锁的同时对installd进行了多次调用
    mInstaller.setWarnIfHeld(mPackages);
    ... 
}
```



#### APK扫描

PKMS的构造函数中调用了 **scanDirTracedLI**方法 来扫描某个目录的apk文件。注意：Android10.0 和 其他低版本扫描的路径是不一样的：Android 10.0中，PKMS主要扫描以下路径的APK信息：

> - /vendor/overlay 系统的APP类别 
> - /product/overlay 系统的APP类别 
> - /product_services/overlay 系统的APP类别
> - /odm/overlay 系统的APP类别 
> - /oem/overlay 系统的APP类别
> - /system/framework 系统的APP类别 
> - /system/priv-app 系统的APP类别
> - /system/app 系统的APP类别
> - /vendor/priv-app 系统的APP类别
> - /vendor/app 系统的APP类别 
> - /odm/priv-app 系统的APP类别
> - /odm/app 系统的APP类别 
> - /oem/app 系统的APP类别 
> - /oem/priv-app 系统的APP类别
> - /product/priv-app 系统的APP类别
> - /product/app 系统的APP类别
> - /product_services/priv-app 系统的APP类别 
> - /product_services/app 系统的APP类别
> - /product_services/priv-app 系统的APP类别

APK的扫描，整体描述图：

![微信图片_20220606222353](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/a83e44b1ae94497caf8825fef62ac685~tplv-k3u1fbpfcp-zoom-1.image)



**总结**：

> 第一步：扫描APK，解析AndroidManifest.xml文件，得到清单文件各个标签内容
>
> 第二步：解析清单文件到的信息由 Package 保存。从该类的成员变量可看出，和 Android 四大组件相关的信息分别由 activites、receivers、providers、services 保存，由于一个 APK 可声明多个组件，因此activites 和 receivers等均声明为 ArrayList





## 五，APK的安装

### 1.安装步骤概述

> 1. 把Apk的信息通过IO流的形式写入到PackageInstaller.Session中
> 2. 调用PackageInstaller.Session的commit方法, 把Apk的信息交给PKMS处理
> 3. 进行Apk的Copy操作, 进行安装



### 2. 用户点击 xxx.apk 文件进行安装, 从 开始安装到完成安装流程

![微信图片_20220606231545](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/90f5d3954f2f45eea6798c385026130a~tplv-k3u1fbpfcp-zoom-1.image)



### 3. APK的安装, 整体描述图

![微信图片_20220606231726](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/d552c63a74af479390fb9b6289ba02e6~tplv-k3u1fbpfcp-zoom-1.image)



点击一个apk后，会弹出安装界面，点击确定按钮后，会进入**PackageInstallerActivity** 的 **bindUi**() 中 的mAlert点击事件, 弹出的安装界面底部显示的是一个diaglog，主要由bindUi构成，上面有 ”**取消**“ 和 ”**安装**“ 两个按钮，点击安装后 调用startInstall()进行安装: 



### 4. 总结

![image-20220606231917586](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/c0e3b343f0b74f87b2bfdf6a408b347d~tplv-k3u1fbpfcp-zoom-1.image)





## 六，权限扫描

此 “PMS之权限扫描” 学习的目标是： PackageManagerService中执行systemReady()后，需求对/system/etc/permissions中的各种xml进行扫描，进行相应的权限存储，让以后可以使用，这就是本次“PMS只权限扫描”学习的目的。



**权限扫描**

> PackageManagerService执行systemReady()时，通过SystemConfig的readPermissionsFromXml()来扫描读取/system/etc/permissions中的xml文件,包括platform.xml和系统支持的各种硬件模块的feature主要工作



#### 整体图：

![微信图片_20220606232143](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/b7c87fe7359a4ea89aabeed55cbaa63a~tplv-k3u1fbpfcp-zoom-1.image)



#### 总结

权限扫描，扫描/system/etc/permissions中的xml，存入相应的结构体中，供之后权限管理使用





## 七，requestPermissions流程解析

### 1. 概述

Google在 Android 6.0 开始引入了权限申请机制，将所有权限分成了**正常权限**和**危险权限**。

注意：App每次在使用**危险权限**时需要动态的申请并得到用户的授权才能使用。

**权限的分类：**

系统权限分为两类：**正常权限 和 危险权限。**

**正常权限**不会直接给用户隐私权带来风险。如果您的应用在其清单中列出了正常权限，系统将自动授予

该权限。

**危险权限**会授予应用访问用户机密数据的权限。如果您的应用在其清单中列出了正常权限，系统将自动

授予该权限。如果您列出了危险权限，则用户必须明确批准您的应用使用这些权限。

```xml
<!-- 权限组：CALENDAR == 日历读取的权限申请 --> 
<uses-permission android:name="android.permission.READ_CALENDAR" /> 
<uses-permission android:name="android.permission.WRITE_CALENDAR" /> 

<!-- 权限组：CAMERA == 相机打开的权限申请 -->
<uses-permission android:name="android.permission.CAMERA" />

<!-- 权限组：CONTACTS == 联系人通讯录信息获取/写入的权限申请 -->
<uses-permission android:name="android.permission.READ_CONTACTS" />
<uses-permission android:name="android.permission.WRITE_CONTACTS" />

<!-- 权限组：LOCATION == 位置相关的权限申请 --> 
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

<!-- 权限组：PHONE == 拨号相关的权限申请 --> 
<uses-permission android:name="android.permission.CALL_PHONE" /> 
<uses-permission android:name="android.permission.READ_PHONE_STATE" /> 

<!-- 权限组：SMS == 短信相关的权限申请 --> 
<uses-permission android:name="android.permission.SEND_SMS" />
<uses-permission android:name="android.permission.READ_SMS" /> 

<!-- 权限组：STORAGE == 读取存储相关的权限申请 --> 
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" /> 
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

**核心函数：**

- **ContextCompat.checkSelfPermission** 

  > 检查应用是否具有某个危险权限。如果应用具有此权限，方法将返回 
  > PackageManager.PERMISSION_GRANTED，并且应用可以继续操作。如果应用不具有此权限，方法将返回 
  > PackageManager.PERMISSION_DENIED，且应用必须明确向用户要求权限。

- **ActivityCompat.requestPermissions** 

  > 应用可以通过这个方法动态申请权限，调用后会弹出一个对话框提示用户授权所申请的权限。

- **ActivityCompat.shouldShowRequestPermissionRationale**

  > 如果应用之前请求过此权限但用户拒绝了请求，此方法将返回 true。如果用户在过去拒绝了权限请求，并在 权限请求系统对话框中选择了 Don't ask again 选项，此方法将返回 false。如果设备规范禁止应用具 有该权限，此方法也会返回 false。 

- **onRequestPermissionsResult** 

  > 当应用请求权限时，系统将向用户显示一个对话框。当用户响应时，系统将调用应用的 onRequestPermissionsResult() 方法，向其传递用户响应，处理对应的场景。



### 2. 权限申请requestPermissions

1. MainActivity 调用 requestPermissions 进行动态权限申请；

2. requestPermissions函数通过隐士意图，激活PackageInstaller的GrantPermissionsActivity界面，让用户选择是否授权；

3. 经过PKMS把相关信息传递给PermissionManagerService处理；

4. PermissionManagerService处理结束后回调给---->PKMS中的onPermissionGranted方法把处理结果返回；

5. PKMS通知过程中权限变化，并调用writeRuntimePermissionsForUserLPr函数让PackageManager的settings记录下相关授 权信息；

   

![微信图片_20220606233013](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/702ba90b2dc8477b8343d705956a142a~tplv-k3u1fbpfcp-zoom-1.image)





### 3. 检查权限流程checkPermission

1. MainActivity会调用checkSelfPermission方法检测是否具有权限（红色区域）
2. 通过实现类ContextImpl的checkPermission方法经由ActivityManager和ActivityManagerService处理（紫色区域）
3. 经过ActivityManager处理后会调用PKMS的checkUidPermission方法把数据传递给PermissionManagerService处理（蓝色）
4. 在PermissionManagerService.checkUidPermission中经过一系列查询返回权限授权的状态（绿色区域）



![微信图片_20220606233217](https://p3-juejin.byteimg.com/tos-cn-i-k3u1fbpfcp/8fd4f3c8e11947f08f465eca9ad0fd3e~tplv-k3u1fbpfcp-zoom-1.image)





## 八，常见问题

### 