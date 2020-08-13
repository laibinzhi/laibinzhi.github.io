---
title: 在Android应用程序配置Segment
date: 2018-09-14 14:59:55
tags:
  - Android
  - 安卓  
  - 数据分析  
  - Segment 
  - Google Analytics
---

# 概述
## 1.什么是Segment?
 Segment是一个单一平台，只需轻按一下开关，即可将用户数据收集，存储和路由到数百个工具。
 
它会为我们处理混乱的分析安装过程，因此我们可以将更多时间用于处理数据，减少跟踪时间。
<!--more-->
## 2.为什么使用Segment?
Segment为我们开发工程师节省了数月的安装和维护分析工具，使营销人员能够快速尝试新工具和测试广告系列，并使BI团队能够将原始数据导出到内部系统和数据库中。

## 3.为什么使用Segment?
分析，营销自动化，电子邮件，用户测试，错误报告和支持工具都需要相同的数据：谁是您的用户以及他们在做什么。

如果没有Segment，您必须单独检测每个工具，即使您向它们发送了所有相同的数据。Segment消除了这些额外的代码并取代了工具安装过程。

您只需将数据发送给我们，然后我们将其翻译并路由到您的所有工具。

使用细分API来跟踪移动应用和网站上的用户事件，例如网页浏览量，点击次数和注册次数。接下来，您可以在Segment的控制面板中切换要使用的营销，产品和分析工具。然后Segment：

- 在一个地方收集和存储您的数据

- 准备并将数据转换为每个工具都能理解的格式

- 将数据发送到指定的工具，因此您无需再次安装跟踪

# 准备工作
### 1. 注册Segment账号和登录
[https://app.segment.com/login](https://app.segment.com/login)
### 2.登录成功之后如下图所示
![image](http://lbz-blog.test.upcdn.net/post/Segment%E7%99%BB%E5%BD%95%E6%88%90%E5%8A%9F.png)
### 3.点击绿色按钮Add Sources添加资源，选择Android
![image](http://lbz-blog.test.upcdn.net/post/Segment%E6%B7%BB%E5%8A%A0%E8%B5%84%E6%BA%90%E9%80%89%E6%8B%A9Android.png)
### 4.点击Connect
![image](http://lbz-blog.test.upcdn.net/post/%E7%82%B9%E5%87%BBconnect.png)
### 填写资源名称，点确定表示我们已经成功创建资源
![image](http://lbz-blog.test.upcdn.net/post/%E5%A1%AB%E5%86%99%E8%B5%84%E6%BA%90%E5%90%8D%E5%AD%97.png)

# Sample
### 1. 申请Write Key
在上一步准备工作的资源面板中，Settings-API Keys-Write Key,就是我们要用到的***WRITE_KEY***
![image](http://lbz-blog.test.upcdn.net/post/write_key.png)
### 2. 安装库
在analytics模块添加到*build.gradle*

```
dependencies {
  compile 'com.segment.analytics.android:analytics:4.+'
}
```
###  3.初始化客户端
最好在*Application*子类中初始化客户端，最好利用构建者模式，因为它提供了最大的灵活性。

```
public class MyApp extends Application {

  @Override 
  public void onCreate() {
    //通过上下文context和segment密钥WRITE_KEY创建Analytics对象
     Analytics analytics = new Analytics.Builder(context, YOUR_WRITE_KEY)
     .trackApplicationLifecycleEvents() 
     .recordScreenViews() 
     .build();
  
    // 将初始化实例设置为全局可访问实例。
    Analytics.setSingletonInstance(analytics);
  }
}
```
***trackApplicationLifecycleEvents*()** 启用此选项可自动记录某些应用程序事件

***recordScreenViews*()**
启用此选项可自动记录屏幕视图！

#### **Notes**:
1. 自动跟踪生命周期事件（Application Opened，Application Installed，Application Updated），是可选的，但强烈建议与核心事件上跑！
2. 这仅安装Segment目标。这意味着您的所有数据都将从服务器端发送到工具。如果您需要捆绑客户端的其他目标，则需要执行一些其他步骤，例如[*Google Analytics*](https://analytics.google.com/analytics/web/)。这一部分稍后再介绍。
3. 您应该只初始化Analytics客户端的一个实例。创建和丢弃这些代价很高，在大多数情况下，您应该坚持使用我们的单例实现来更轻松地使用SDK。

###  4.添加权限

```
 <!-- Required for internet. -->
<uses-permission android:name="android.permission.INTERNET"/>
```
### 5.Identify鉴定
*identify*允许您将用户绑定到他们的操作并记录有关他们的特征。它包含唯一的用户ID以及您了解的任何可选特征。

建议identify在首次创建用户帐户时（或者登录时）调用一次，并且仅在其特征发生变化时再次识别。

我们在*MainActivity*中*OnCreate*()写下面代码
```
String email = "laibinzhi@gmail.com";
String username = "laibinzhi";
String userID = "001";
//以上模拟登录逻辑后获取到的个人信息
Traits traits = new Traits();
traits.putEmail(email);
traits.putUsername(username);
Analytics.with(this).identify(userID, traits, new Options());
```
然后，我们在资源面板的Debugger中看到出现如下图两行记录，说明我们已经连接成功，客户端已经和我们的Segment服务器正式绑定下来。而在右侧的面板，我们则可以看到我们的用户信息。
![image](http://lbz-blog.test.upcdn.net/post/%E9%89%B4%E5%AE%9Adebugger.png)

### 6.Screen屏幕
该*screen*方法允许您在用户看到移动应用程序的屏幕时进行记录，以及有关正在查看的页面的可选附加信息。

只要用户在您的应用中打开屏幕，您就会想要将事件记录为屏事件。这可能是视图，片段，对话或活动，具体取决于您的应用程序。

并非所有服务都支持屏幕，因此当显式不支持时，屏幕方法将跟踪为具有相同参数的事件。

接下来我们继续在我们的*MainActivity*的*OnCreate()*方法加入屏幕跟踪

```
Analytics.with(this).screen("MainActivity页面", new Properties().putValue("time",DateFormat.format("dd-MM-yyyy HH:mm:ss", new Date()).toString()));
```
在资源面板中出现了一个MainActivity页面以及右边出现他所对应的值
![image](http://lbz-blog.test.upcdn.net/post/segment%E5%B1%8F%E5%B9%95.png)

### 7.跟踪Track
track允许您记录用户执行的操作。每个动作都会触发我们称之为“事件”的事件，事件也可能具有相关属性。

首先，SDK可以使用我们的原生移动规范自动跟踪一些关键的常见事件，例如Application Installed，Application Updated和Application Opened。只需在初始化期间启用此选项。

您还需要跟踪作为移动应用程序成功指标的事件，例如“已注册”，“已购买项目”或“已添加书签”。又或者一个视频播放器，已暂停已播放之类的。

我们在MainActivit增加一个按钮和点击事件监听器，记录它的事件，

```
 findViewById(R.id.btn_start).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Analytics.with(MainActivity.this).track("开始点击", new Properties().putValue("type", "开始"));
            }
        });
```
再看资源面板，已经成功记录点击事件
![image](http://lbz-blog.test.upcdn.net/post/segment%E8%B7%9F%E8%B8%AA.png)

###  8.更多
关于更多的Segment的api请参考[这里](https://segment.com/docs/sources/mobile/android/)

### 9.Segment和Google Analytics绑定
- > 首先你得注册一个Google Analytics账号并且登录（需要谷歌账号）。然后新建一个项目，获取到一个跟踪id
- >在Segment资源面板Overview页面的绿色按钮Add Destination 点击，然后选择Google Analytics，然后点击Configure Google Analytics,选择Segment你的项目，最后点击Confirm Source,出现下图所示
![image](http://lbz-blog.test.upcdn.net/post/segment_google.png)
勾选***Google* Analytics Setting**
然后点击***Mobile* Tracking ID**，然后把第一步的跟踪id填写上去。
- > 在你的*build.gradle*文件加上
  
```
compile 'com.segment.analytics.android.integrations:google-analytics:+'

```
- > 修改一下初始化Segment客户端，在build参数后添加

```
builder.use(GoogleAnalyticsIntegration.FACTORY);

```
-> 最后，重新运行一次程序，打开Google Analytics，你会发现，在Segment捕捉记录下来的事件也会在这里出现。如图
![image](http://lbz-blog.test.upcdn.net/post/%E8%B0%B7%E6%AD%8C%E5%88%86%E6%9E%90.png)

### 10.结语
到此，Segment的Android客户端配置简介配置到此为止，更多新的有趣的用法，可以参考[官方开发文档](https://segment.com/docs/sources/mobile/android/)。
