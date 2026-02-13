---
title: 实战：将 Android 多模块应用迁移到 Kotlin Multiplatform + Compose Multiplatform
date: 2026-02-13
tags:
  - Android
  - KMP
  - CMP
  - IOS
---

# 实战：将 Android 多模块应用迁移到 Kotlin Multiplatform + Compose Multiplatform

最近把自己的 NBA 数据应用 HoopsNow 从纯 Android 多模块架构迁移到了 KMP + CMP，实现了 Android/iOS 共享一套代码。这篇文章记录整个迁移过程中的思路、踩坑和最终方案。

<!--more-->


## 项目背景

HoopsNow 是一个 NBA 数据展示应用，功能包括比赛比分、球队信息、球员搜索和收藏管理。迁移前的架构参考了 Google 的 [Now in Android](https://github.com/android/nowinandroid) 项目，是一个标准的 Android 多模块架构：

```
hoopsnow/
├── app/                        # 入口 + Navigation3
├── core/                       # 9 个核心模块
│   ├── common/                 # 工具类
│   ├── data/                   # Repository
│   ├── database/               # Room
│   ├── datastore/              # DataStore
│   ├── designsystem/           # 主题
│   ├── model/                  # 数据模型
│   ├── network/                # Ktor
│   ├── testing/                # 测试工具
│   └── ui/                     # 共享 UI
├── feature/                    # 4 个功能模块 (api/impl)
│   ├── games/
│   ├── teams/
│   ├── players/
│   └── favorites/
└── build-logic/                # 7 个 Convention Plugins
```

技术栈：**Hilt** + **Navigation3** + **Room** + **ViewModel** + **Coil**

这套架构在纯 Android 场景下很好用，模块边界清晰，构建并行度高。但当我想把应用扩展到 iOS 时，这些 Android 专属的库就成了障碍。

## 为什么选择 KMP + CMP

考虑过几个方案：

| 方案 | 优点 | 缺点 |
|------|------|------|
| Flutter | 生态成熟，热重载 | 需要重写全部代码，Dart 语言 |
| React Native | Web 开发者友好 | 性能开销，桥接复杂 |
| KMP + 原生 UI | 共享逻辑，原生体验 | 需要写两套 UI |
| KMP + CMP | 共享逻辑 + UI，Kotlin 全栈 | CMP iOS 端相对年轻 |

最终选了 KMP + CMP，原因很简单：现有代码是 Kotlin + Compose，迁移成本最低，UI 也能共享。

## 技术栈替换

迁移的核心就是把 Android 专属库替换为 KMP 兼容的���：

| 功能 | 迁移前 | 迁移后 | 迁移难度 |
|------|--------|--------|----------|
| 依赖注入 | Hilt | **Koin 4.0** | ⭐⭐ |
| 导航 | Navigation3 | **Voyager 1.1.0-beta03** | ⭐⭐⭐ |
| 数据库 | Room | **SQLDelight 2.0** | ⭐⭐⭐ |
| 状态管理 | ViewModel | **Voyager ScreenModel** | ⭐ |
| 图片加载 | Coil | **Coil 3 (KMP)** | ⭐ |
| 网络 | Ktor (Android) | **Ktor 3.0 (KMP)** | ⭐ |
| UI | Jetpack Compose | **Compose Multiplatform 1.7** | ⭐ |

下面逐个说说迁移细节。

## 一、创建 shared 模块

第一步是创建 KMP 共享模块。`shared/build.gradle.kts` 的核心配置：

```kotlin
plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.compose.multiplatform)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.sqldelight)
}

kotlin {
    androidTarget {
        compilerOptions { jvmTarget.set(JvmTarget.JVM_17) }
    }

    listOf(iosX64(), iosArm64(), iosSimulatorArm64()).forEach {
        it.binaries.framework {
            baseName = "Shared"
            isStatic = true
        }
    }

    sourceSets {
        commonMain.dependencies {
            implementation(compose.runtime)
            implementation(compose.foundation)
            implementation(compose.material3)
            implementation(compose.materialIconsExtended)
            // Ktor, SQLDelight, Koin, Voyager, Coil ...
        }
        androidMain.dependencies {
            implementation(libs.ktor.client.okhttp)
            implementation(libs.sqldelight.android.driver)
        }
        iosMain.dependencies {
            implementation(libs.ktor.client.darwin)
            implementation(libs.sqldelight.native.driver)
        }
    }
}
```

## 二、数据库迁移：Room → SQLDelight

这是迁移中工作量最大的部分。Room 不支持 KMP，必须换成 SQLDelight。

### 定义 .sq 文件

SQLDelight 用 `.sq` 文件定义表结构和查询，放在 `commonMain/sqldelight/` 目录下：

```sql
-- Team.sq
CREATE TABLE TeamEntity (
    id INTEGER PRIMARY KEY NOT NULL,
    conference TEXT NOT NULL,
    division TEXT NOT NULL,
    city TEXT NOT NULL,
    name TEXT NOT NULL,
    fullName TEXT NOT NULL,
    abbreviation TEXT NOT NULL
);

getAll: SELECT * FROM TeamEntity;
getById: SELECT * FROM TeamEntity WHERE id = ?;
upsert: INSERT OR REPLACE INTO TeamEntity VALUES (?, ?, ?, ?, ?, ?, ?);
```

### 平台 Driver

通过 `expect/actual` 为不同平台提供数据库驱动：

```kotlin
// commonMain
expect class DatabaseDriverFactory {
    fun createDriver(): SqlDriver
}

// androidMain
actual class DatabaseDriverFactory(private val context: Context) {
    actual fun createDriver(): SqlDriver =
        AndroidSqliteDriver(NbaDatabase.Schema, context, "nba.db")
}

// iosMain
actual class DatabaseDriverFactory {
    actual fun createDriver(): SqlDriver =
        NativeSqliteDriver(NbaDatabase.Schema, "nba.db")
}
```

### 踩坑：SQLDelight 属性名

SQLDelight 生成的 Queries 属性名基于 `.sq` 文件名，不是表名。比如 `Game.sq` 生成 `database.gameQueries`，不是 `database.gameEntityQueries`。这个坑让我排查了好一会儿。

### 踩坑：Kotlin 类型推断

SQLDelight 的链式 mapper 调用会让 Kotlin 的类型推断犯迷糊。解决方案是写显式的扩展函数：

```kotlin
fun TeamEntity.toTeam(): Team = Team(
    id = id.toInt(),
    conference = conference,
    division = division,
    city = city,
    name = name,
    fullName = fullName,
    abbreviation = abbreviation,
)
```

## 三、依赖注入：Hilt → Koin

Hilt 依赖 Android 的注解处理器（KSP），不支持 KMP。Koin 是纯 Kotlin 实现，天然跨平台。

```kotlin
// commonMain - KoinModules.kt
val sharedModule = module {
    // Network
    single<NbaNetworkDataSource> { KtorNbaNetwork(get()) }

    // Database
    single { get<DatabaseDriverFactory>().createDriver() }
    single { NbaDatabase(get()) }

    // Repositories
    single<GamesRepository> { OfflineFirstGamesRepository(get(), get()) }
    single<TeamsRepository> { OfflineFirstTeamsRepository(get(), get()) }
    single<PlayersRepository> { OfflineFirstPlayersRepository(get(), get()) }
    single<FavoritesRepository> { OfflineFirstFavoritesRepository(get(), get()) }

    // ScreenModels
    factory { GamesListScreenModel(get()) }
    factory { params -> GameDetailScreenModel(params.get(), get()) }
    // ...
}

// 平台模块通过 expect/actual 提供
expect fun platformModule(): Module
```

平台模块只需要提供 HTTP 引擎和数据库驱动：

```kotlin
// androidMain
actual fun platformModule(): Module = module {
    single<HttpClientEngine> { OkHttp.create() }
    single { DatabaseDriverFactory(get()) }
}

// iosMain
actual fun platformModule(): Module = module {
    single<HttpClientEngine> { Darwin.create() }
    single { DatabaseDriverFactory() }
}
```

迁移体验：Hilt 的 `@HiltViewModel` + `@Inject constructor` 全部删掉，换成 Koin 的 `factory { }` 声明。代码量反而少了。

## 四、导航：Navigation3 → Voyager

导航是迁移中设计决策最多的部分。Voyager 提供了 `TabNavigator` + `Navigator` 的组合，很适合底部 Tab + 页面栈的场景。

### Tab 定义

```kotlin
object GamesTab : Tab {
    override val options @Composable get() = TabOptions(
        index = 0u,
        title = "Games",
        icon = rememberVectorPainter(Icons.Default.SportsBasketball),
    )

    @Composable
    override fun Content() {
        Navigator(GamesListScreen()) { navigator ->
            SlideTransition(navigator)
        }
    }
}
```

每个 Tab 内嵌独立的 `Navigator`，Tab 切换时各自的导航栈互不影响。

### Screen 定义

```kotlin
class GamesListScreen : Screen {
    @Composable
    override fun Content() {
        val screenModel = koinScreenModel<GamesListScreenModel>()
        val uiState by screenModel.uiState.collectAsState()
        // UI ...
    }
}
```

### 页面间传参

Voyager 通过构造函数传参，简单直接：

```kotlin
class GameDetailScreen(private val gameId: Int) : Screen { ... }

// 导航
navigator.push(GameDetailScreen(gameId = 123))
```

Koin 端用 `parametersOf` 传递：

```kotlin
// 定义
factory { params -> GameDetailScreenModel(params.get(), get()) }

// 使用
val screenModel = koinScreenModel<GameDetailScreenModel> { parametersOf(gameId) }
```

### 主入口

```kotlin
@Composable
fun HoopsNowApp() {
    HoopsNowTheme {
        TabNavigator(GamesTab) {
            Scaffold(
                bottomBar = {
                    NavigationBar {
                        TabNavigationItem(GamesTab)
                        TabNavigationItem(TeamsTab)
                        TabNavigationItem(PlayersTab)
                        TabNavigationItem(FavoritesTab)
                    }
                },
            ) {
                CurrentTab()
            }
        }
    }
}
```

## 五、状态管理：ViewModel → ScreenModel

这是最简单的一步。Voyager 的 `ScreenModel` 和 `ViewModel` 几乎一模一样：

```kotlin
// 迁移前
@HiltViewModel
class GamesListViewModel @Inject constructor(
    private val gamesRepository: GamesRepository,
) : ViewModel() {
    val uiState = gamesRepository.getGames()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), Loading)
}

// 迁移后
class GamesListScreenModel(
    private val gamesRepository: GamesRepository,
) : ScreenModel {
    val uiState = gamesRepository.getGames()
        .stateIn(screenModelScope, SharingStarted.WhileSubscribed(5000), Loading)
}
```

改动点：
- 删除 `@HiltViewModel` 和 `@Inject constructor`
- `ViewModel()` → `ScreenModel`
- `viewModelScope` → `screenModelScope`
- `collectAsStateWithLifecycle()` → `collectAsState()`（CMP 中没�� AndroidX Lifecycle）

## 六、Android 入口精简

迁移后 `app` 模块只剩两个文件：

```kotlin
// HoopsNowApplication.kt
class HoopsNowApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidContext(this@HoopsNowApplication)
            modules(sharedModule, platformModule())
        }
    }
}

// MainActivity.kt
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(...)
        setContent {
            CompositionLocalProvider(
                LocalTeamLogos provides TeamLogoProvider.getAllLogos(),
                LocalPlayerHeadshot provides PlayerHeadshotProvider::getHeadshotUrl,
            ) {
                HoopsNowApp()  // 来自 shared 模块
            }
        }
    }
}
```

## 七、iOS 接入

iOS 端更简单，只需要一个 SwiftUI 壳：

```swift
// iOSApp.swift
@main
struct iOSApp: App {
    init() {
        KoinHelperKt.doInitKoin()
    }
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}

// ContentView.swift
struct ContentView: View {
    var body: some View {
        ComposeView().ignoresSafeArea(.all)
    }
}

struct ComposeView: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        MainViewControllerKt.MainViewController()
    }
    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {}
}
```

shared 模块中提供 iOS 入口：

```kotlin
// iosMain - MainViewController.kt
fun MainViewController() = ComposeUIViewController { HoopsNowApp() }
```

就这样，iOS 端就能跑起来了。整个 Compose UI 通过 `ComposeUIViewController` 嵌入 SwiftUI。

## 八、清理旧代码

迁移完成后，大量旧文件可以删除：

- `core/` — 9 个旧 Android 模块全部删除
- `feature/` — 4 个功能模块全部删除
- `app/navigation/` — 旧 Navigation3 代码
- `build-logic/` 中的 6 个 Convention Plugin（Hilt、Room、Feature、Library 等）
- `libs.versions.toml` 中的 Hilt、KSP 相关声明

从 20+ 个模块精简到 2 个（`app` + `shared`），`settings.gradle.kts` 清爽了很多。

## 迁移后的项目结构

```
hoopsnow/
├── app/                                # Android 入口（2 个文件）
├── shared/                             # KMP 共享模块
│   └── src/
│       ├── commonMain/                 # 全部业务逻辑 + UI
│       │   ├── kotlin/.../
│       │   │   ├── core/               # 数据层（model, data, database, network��
│       │   │   ├── di/                 # Koin 模块
│       │   │   └── ui/                 # UI 层（screens, components, theme, navigation）
│       │   └── sqldelight/             # 数据库定义
│       ├── androidMain/                # Android 平台实现
│       └── iosMain/                    # iOS 平台实现
├── iosApp/                             # iOS 入口（2 个 Swift 文件）
└── build-logic/                        # Convention Plugins（精简）
```

## 踩坑总结

### 1. SQLDelight 属性名
生成的 Queries 属性名基于 `.sq` 文件名（`gameQueries`），不是 `CREATE TABLE` 的表名（`gameEntityQueries`）。

### 2. collectAsStateWithLifecycle 不可用
这是 AndroidX Lifecycle 的扩展，CMP 中用 `collectAsState()` 替代。ScreenModel 会在 Screen dispose 时自动取消 scope，不用担心泄漏。

### 3. Kotlin 类型推断与 SQLDelight
链式 mapper 调用时类型推断可能失败，写显式的 `toModel()` 扩展函数解决。

### 4. Material Icons Extended
`Icons.Default.StarBorder`、`Icons.Default.OpenInNew` 等图标需要额外添加 `compose.materialIconsExtended` 依赖。

### 5. Koin ScreenModel 参数传递
带参数的 ScreenModel 需要用 `factory { params -> }` 定义，使用时通过 `koinScreenModel { parametersOf(...) }` 传入。

### 6. iOS Framework 编译
每次修改 shared 代码后需要重新编译 Framework。开发阶段建议在 Xcode Build Phase 中添加自动编译脚本。

## 迁移收益

| 指标 | 迁移前 | 迁移后 |
|------|--------|--------|
| 模块数量 | 20+ | 2 (app + shared) |
| 支持平台 | Android | Android + iOS |
| UI 代码共享 | 0% | 100% |
| 业务逻辑共享 | 0% | 100% |
| build.gradle 文件 | 20+ | 3 |
| Convention Plugins | 7 | 2 |

最大的收益是 iOS 端几乎零成本接入 — 只需要两个 Swift 文件就能跑起完整的应用。

## 依赖版本参考

| 库 | 版本 |
|----|------|
| Kotlin | 2.0.21 |
| Compose Multiplatform | 1.7.3 |
| Ktor | 3.0.3 |
| SQLDelight | 2.0.2 |
| Koin | 4.0.0 |
| Voyager | 1.1.0-beta03 |
| Coil 3 | 3.0.4 |
| kotlinx-serialization | 1.7.3 |
| kotlinx-datetime | 0.6.1 |
| Coroutines | 1.9.0 |

## 总结

整个迁移花了大约一周时间，其中数据库迁移（Room → SQLDelight）和导航迁移（Navigation3 → Voyager）占了大部分工作量。网络层（Ktor）和序列化（kotlinx-serialization）本身就是 KMP 库，基本不用改。

如果你的 Android 项目已经在用 Kotlin + Compose，迁移到 KMP + CMP 的成本比想象中低很多。最大的障碍是 Room 和 Hilt 这两个 Android 专属库的替换，但 SQLDelight 和 Koin 都是成熟的替代方���。

项目源码：[GitHub - laibinzhi/hoopsnow](https://github.com/laibinzhi/hoopsnow)（cmp 分支）
