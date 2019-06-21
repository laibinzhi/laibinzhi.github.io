---
title: Flutter学习-创建和使用Flutter的路由与导航
date: 2019-06-21 14:24:53
tags:
  - Android
  - 安卓  
---

# 核心概念

管理多个页面时有两个核心概念和类：Route和 Navigator。 一个route是一个屏幕或页面的抽象，Navigator是管理route的Widget。Navigator可以通过route入栈和出栈来实现页面之间的跳转。

<!--more-->
# 第一种方式（静态路由的注册）

```
import 'package:flutter/material.dart';

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    // TODO: implement build
    return new MaterialApp(
      title: 'Flutter Demo',
      home: MyHomePage(title: '首页'),
      routes: <String, WidgetBuilder>{
        '/a': (BuildContext context) => new MyPage(
              title: 'A页面',
            ),
        '/b': (BuildContext context) => new MyPage(
              title: 'B页面',
            ),
        '/c': (BuildContext context) => new MyPage(
              title: 'C页面',
            ),
      },
    );
  }
}

class MyHomePage extends StatefulWidget {
  final String title;

  MyHomePage({Key key, this.title}) : super(key: key);

  @override
  State<StatefulWidget> createState() {
    // TODO: implement createState
    return _MyHomePageState();
  }
}

class _MyHomePageState extends State<MyHomePage> {
  @override
  Widget build(BuildContext context) {
    // TODO: implement build
    return new Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
      ),
      body: new Row(
        children: <Widget>[
          new RaisedButton(
            onPressed: () {
              Navigator.of(context).pushNamed('/a');
            },
            child: Text('A按钮'),
          ),
          new RaisedButton(
            onPressed: () {
              Navigator.of(context).pushNamed('/b');
            },
            child: Text('B按钮'),
          ),
          new RaisedButton(
            onPressed: () {
              Navigator.of(context).pushNamed('/c');
            },
            child: Text('C按钮'),
          ),
        ],
      ),
    );
  }
}

class MyPage extends StatelessWidget {
  final String title;

  MyPage({Key key, this.title}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    // TODO: implement build
    return new Scaffold(
      appBar: AppBar(
        title: Text(title),
      ),
    );
  }
}

```
# 第二种方式（动态路由的注册）

```
import 'package:flutter/material.dart';

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    // TODO: implement build
    return MaterialApp(
      title: 'WAY 1',
      home: MyIndexApp(title: '这是首页'),
    );
  }
}

class MyIndexApp extends StatefulWidget {
  final String title;

  MyIndexApp({Key key, this.title}) : super(key: key);

  @override
  State<StatefulWidget> createState() {
    // TODO: implement createState
    return _MyIndexAppState();
  }
}

class _MyIndexAppState extends State<MyIndexApp> {
  @override
  Widget build(BuildContext context) {
    // TODO: implement build
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
      ),
      body: Center(
        child: Text('点击浮动按钮跳转到下一页'),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _nextPage,
        child: Icon(Icons.add),
      ),
    );
  }

  void _nextPage() {
    setState(() {
      Navigator.of(context)
          .push(new MaterialPageRoute(builder: (BuildContext context) {
        return new Scaffold(
          appBar: AppBar(
            title: Text('新的页面'),
          ),
          body: Center(
            child: Text('这是新的页面，点击返回上一页'),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: _ShangePage,
            child: Icon(Icons.replay),
          ),
        );
      }));
    });
  }

  void _ShangePage() {
    Navigator.of(context).pop();
  }
}

```
