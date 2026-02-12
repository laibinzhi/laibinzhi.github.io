---
title: 从零到一：用 Now in Android 架构打造一款 NBA 应用
date: 2026-02-11 00:00:00
tags:
  - Android
  - Jetpack
  - Kotlin
  - MVVM
categories:
  - Android
---

# 从零到一：用 Now in Android 架构打造一款 NBA 应用

> 本文以开源项目 **HoopsNow** 为例，深度拆解 Google 官方推荐的 Now in Android (NIA) 架构在真实项目中的落地实践。涵盖多模块拆分、Convention Plugins、Feature API/Impl 分层、离线优先数据层、Navigation 3 导航以及 Jetpack Compose + MVVM 状态管理等核心主题。

## 目录

- [为什么选择 NIA 架构](#为什么选择-nia-架构)
- [项目概览](#项目概览)
- [模块化设计：从单体到多模块](#模块化设计从单体到多模块)
- [Convention Plugins：告别重复的构建配置](#convention-plugins告别重复的构建配置)
- [Feature API/Impl 分层模式](#feature-apiimpl-分层模式)
- [数据层：离线优先架构](#数据层离线优先架构)
- [Navigation 3：类型安全的导航系统](#navigation-3类型安全的导航系统)
- [ViewModel + UiState：单向数据流实践](#viewmodel--uistate单向数据流实践)
- [Hilt 依赖注入：把一切粘合在一起](#hilt-依赖注入把一切粘合在一起)
- [总结与收获](#总结与收获)

---

<!--more-->


## 为什么选择 NIA 架构

Google 在 2022 年推出了 [Now in Android](https://github.com/android/nowinandroid) 示例项目，它不是一个简单的 Demo，而是 Google 对「现代 Android 应用该怎么写」这个问题给出的官方答案。

NIA 架构的核心理念：

- **模块化** — 按功能拆分模块，提升构建速度和团队协作效率
- **关注点分离** — UI、数据、业务逻辑各司其职
- **离线优先** — 本地数据库作为唯一数据源（Single Source of Truth）
- **单向数据流 (UDF)** — 状态向下流动，事件向上流动
- **Convention Plugins** — 统一构建配置，消除模块间的 build.gradle 重复

但 NIA 官方项目本身过于庞大（60+ 模块），对于想要学习的开发者来说，入门门槛不低。因此，我做了 **HoopsNow** — 一个结构清晰、规模适中的 NBA 数据应用，作为 NIA 架构的教学实践。

---

## 项目概览

**HoopsNow** 是一款 NBA 数据应用，功能包括：

| 功能 | 说明 |
|------|------|
| 比赛 | 查看每日 NBA 比赛比分与赛程 |
| 球队 | 浏览 30 支球队信息（东/西部分区） |
| 球员 | 搜索球员、查看球员详情 |
| 收藏 | 收藏喜爱的球队和球员 |

**技术栈一览：**

| 类别 | 技术 |
|------|------|
| 语言 | Kotlin |
| UI | Jetpack Compose + Material 3 |
| 导航 | Navigation 3 |
| 依赖注入 | Hilt |
| 数据库 | Room |
| 偏好存储 | DataStore |
| 网络 | Retrofit + OkHttp + Kotlin Serialization |
| 异步 | Coroutines + Flow |
| 构建 | Convention Plugins + Typesafe Project Accessors |

---

## 模块化设计：从单体到多模块

### 为什么要多模块？

单模块项目在初期很方便，但随着代码量增长，你会遇到：

1. **构建时间膨胀** — 改一行代码，整个项目重新编译
2. **依赖混乱** — 任何类都可以互相引用，耦合度爆炸
3. **团队协作冲突** — 多人修改同一模块，频繁冲突
4. **代码边界模糊** — 业务逻辑和 UI 混在一起

多模块化解决了这些问题。Gradle 可以并行编译独立模块，模块之间有明确的依赖关系，改动一个模块不会影响其他模块的编译。

### HoopsNow 模块结构

```
HoopsNow/
├── app/                          # 应用壳模块 — 导航、Scaffold、入口
│
├── build-logic/                  # Convention Plugins — 统一构建配置
│   └── convention/
│
├── feature/                      # 功能模块（每个功能 = api + impl）
│   ├── games/
│   │   ├── api/                  # 导航契约：GamesNavKey, GameDetailNavKey
│   │   └── impl/                 # 实现：Screen, ViewModel, UiState
│   ├── teams/
│   │   ├── api/
│   │   └── impl/
│   ├── players/
│   │   ├── api/
│   │   └── impl/
│   └── favorites/
│       ├── api/
│       └── impl/
│
└── core/                         # 核心模块
    ├── model/                    # 领域模型（纯 Kotlin，无 Android 依赖）
    ├── data/                     # Repository 接口 + 离线优先实现
    ├── database/                 # Room 数据库、DAO、Entity
    ├── network/                  # Retrofit API、网络模型
    ├── datastore/                # DataStore 用户偏好
    ├── common/                   # 公共工具类
    ├── designsystem/             # 主题、颜色、通用组件
    ├── ui/                       # 跨功能共享 UI 组件
    └── testing/                  # 测试工具、Fake 实现
```

总计 **19 个模块**，结构清晰：

- **app** — 只负责"粘合"，把各功能模块组装起来
- **feature** — 每个业务功能独立成模块
- **core** — 可复用的基础设施

### 模块依赖关系

```
app
 ├── feature:games:impl
 ├── feature:teams:impl
 ├── feature:players:impl
 ├── feature:favorites:impl
 ├── feature:*:api （所有 api 模块）
 └── core:*

feature:games:impl
 ├── feature:games:api
 ├── core:data
 ├── core:model
 ├── core:ui
 └── core:designsystem

core:data
 ├── core:model
 ├── core:database
 └── core:network
```

**关键原则：feature 模块之间不直接依赖 impl，只依赖 api。** 这保证了模块间的松耦合。

---

## Convention Plugins：告别重复的构建配置

### 痛点

多模块项目有一个常见问题：每个模块的 `build.gradle.kts` 都要写一堆重复配置 — `compileSdk`、`minSdk`、`jvmTarget`、Compose 配置、Hilt 配置……

改一个版本号，要改 19 个文件？这不可接受。

### 解决方案：Convention Plugins

Convention Plugins 是 Gradle 的一个强大特性 — 你可以把公共的构建逻辑封装成插件，模块只需一行代码就能应用。

HoopsNow 定义了 **8 个 Convention Plugin**：

| 插件 ID | 作用 |
|---------|------|
| `hoopsnow.android.application` | Android Application 基础配置 |
| `hoopsnow.android.application.compose` | Application + Compose 支持 |
| `hoopsnow.android.library` | Android Library 基础配置 |
| `hoopsnow.android.library.compose` | Library + Compose 支持 |
| `hoopsnow.android.feature` | Feature 模块一站式配置 |
| `hoopsnow.android.hilt` | Hilt 依赖注入配置 |
| `hoopsnow.android.room` | Room 数据库配置 |
| `hoopsnow.jvm.library` | 纯 JVM 库（无 Android 依赖） |

### 示例：AndroidFeatureConventionPlugin

这是最能体现 Convention Plugin 威力的一个：

```kotlin
class AndroidFeatureConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            // 自动应用 Library + Compose + Hilt 插件
            pluginManager.apply {
                apply("hoopsnow.android.library")
                apply("hoopsnow.android.library.compose")
                apply("hoopsnow.android.hilt")
            }

            extensions.configure<LibraryExtension> {
                defaultConfig {
                    testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
                }
            }

            // 自动添加 Feature 模块的公共依赖
            dependencies {
                add("implementation", project(":core:ui"))
                add("implementation", project(":core:designsystem"))
                add("implementation", project(":core:model"))

                add("implementation", libs.findLibrary("androidx-hilt-navigation-compose").get())
                add("implementation", libs.findLibrary("androidx-lifecycle-runtime-compose").get())
                add("implementation", libs.findLibrary("androidx-lifecycle-viewmodel-compose").get())
            }
        }
    }
}
```

**一个插件 = Library 配置 + Compose 配置 + Hilt 配置 + 公共依赖。**

### 使用后的 build.gradle.kts

看看 Feature 模块的 `build.gradle.kts` 变得多简洁：

```kotlin
// feature/games/impl/build.gradle.kts
plugins {
    alias(libs.plugins.hoopsnow.android.feature)
    alias(libs.plugins.hoopsnow.android.library.compose)
    alias(libs.plugins.hoopsnow.android.hilt)
}

android {
    namespace = "com.hoopsnow.nba.feature.games.impl"
}

dependencies {
    implementation(projects.feature.games.api)
    implementation(projects.core.data)
}
```

注意 `projects.feature.games.api` — 这是 **Typesafe Project Accessors**，在 `settings.gradle.kts` 中启用：

```kotlin
enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")
```

相比字符串 `project(":feature:games:api")`，类型安全的访问器能在编译期发现拼写错误。

### 公共配置：ProjectExtensions.kt

所有 Android 模块共享的 Kotlin/Android 配置也被提取了出来：

```kotlin
internal fun CommonExtension<*, *, *, *, *, *>.configureKotlinAndroid(project: Project) {
    compileSdk = project.libs.findVersion("compileSdk").get().toString().toInt()

    defaultConfig {
        minSdk = project.libs.findVersion("minSdk").get().toString().toInt()
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    project.configureKotlin()
}

internal fun CommonExtension<*, *, *, *, *, *>.configureAndroidCompose(project: Project) {
    buildFeatures {
        compose = true
    }

    project.dependencies {
        val bom = project.libs.findLibrary("androidx-compose-bom").get()
        add("implementation", platform(bom))
        add("androidTestImplementation", platform(bom))
    }
}
```

版本号全部来自 `libs.versions.toml`，**改一处，全局生效**。

---

## Feature API/Impl 分层模式

这是 HoopsNow 中最有特色的架构决策之一。

### 为什么要分 api 和 impl？

假设你有 `feature:games` 和 `feature:teams` 两个模块。在比赛详情页面，用户点击球队名称要跳转到球队详情页面。这意味着 `feature:games:impl` 需要知道如何导航到 `feature:teams` 的页面。

**如果直接依赖 impl：**

```
feature:games:impl → feature:teams:impl  ❌
```

问题来了：
- `teams:impl` 的任何改动都会触发 `games:impl` 重新编译
- 两个 impl 互相依赖会造成循环依赖
- impl 的内部实现（ViewModel、Screen）被暴露

**用 api/impl 分离：**

```
feature:games:impl → feature:teams:api  ✅
feature:teams:impl → feature:teams:api  ✅
```

### api 模块只包含什么？

**仅导航契约 — NavKey 定义：**

```kotlin
// feature/games/api/.../GamesNavKeys.kt
@Serializable
object GamesNavKey : NavKey

@Serializable
data class GameDetailNavKey(val gameId: Int) : NavKey
```

就这么简单。api 模块极度轻量：
- 没有 Compose 依赖
- 没有 ViewModel
- 没有业务逻辑
- 只有 Kotlin Serialization 和 Navigation 3 Runtime

对应的 `build.gradle.kts`：

```kotlin
// feature/games/api/build.gradle.kts
plugins {
    alias(libs.plugins.hoopsnow.android.library)
    alias(libs.plugins.kotlin.serialization)
}

dependencies {
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.androidx.navigation3.runtime)
}
```

### impl 模块包含什么？

所有的具体实现：

```
feature/games/impl/
├── GamesUiState.kt         # UI 状态的密封接口
├── GamesListViewModel.kt   # ViewModel 业务逻辑
├── GamesListScreen.kt      # Compose UI
├── GameDetailViewModel.kt
└── GameDetailScreen.kt
```

### 这种模式的好处

1. **编译隔离** — `games:impl` 的改动不会影响依赖 `games:api` 的其他模块
2. **禁止循环依赖** — 模块间只能通过轻量的 api 通信
3. **构建加速** — api 模块极少变化，大部分编译可以增量跳过
4. **封装性** — impl 中的 ViewModel、Screen 等实现细节对外不可见

---

## 数据层：离线优先架构

### 三层模型转换

NIA 架构中，数据经历三次模型转换：

```
Network Model → Domain Model → Entity (Database)
NetworkGame   → Game         → GameEntity
```

**为什么需要三套模型？**

- **NetworkGame** — 匹配 API JSON 结构，包含 `@SerialName` 注解
- **Game** — 纯领域模型，UI 层直接使用，不依赖任何框架
- **GameEntity** — Room 数据库实体，扁平化结构方便存储

```kotlin
// 领域模型 — 纯 Kotlin，无框架依赖
@Serializable
data class Game(
    val id: Int,
    val date: String,
    val season: Int,
    val homeTeamScore: Int,
    val visitorTeamScore: Int,
    val homeTeam: Team,
    val visitorTeam: Team,
    val status: String = if (homeTeamScore > 0 || visitorTeamScore > 0) "Final" else "Scheduled",
)
```

```kotlin
// 数据库实体 — 扁平化，嵌套对象拆为独立字段
@Entity(tableName = "games")
data class GameEntity(
    @PrimaryKey val id: Int,
    val date: String,
    val season: Int,
    val homeTeamScore: Int,
    val visitorTeamScore: Int,
    val status: String,
    // 主队字段
    val homeTeamId: Int,
    val homeTeamName: String,
    val homeTeamFullName: String,
    val homeTeamAbbreviation: String,
    // 客队字段...
)
```

模型之间通过扩展函数转换：

```kotlin
// Network → Domain
fun NetworkGame.asExternalModel(): Game = Game(
    id = id,
    date = date,
    homeTeam = homeTeam?.asExternalModel() ?: /* fallback */,
    visitorTeam = visitorTeam?.asExternalModel() ?: /* fallback */,
    ...
)

// Entity → Domain
fun GameEntity.asExternalModel(): Game = Game(...)

// Domain → Entity
fun Game.asEntity(): GameEntity = GameEntity(...)
```

### Repository 模式

Repository 接口定义在 `core:data` 模块中：

```kotlin
interface GamesRepository {
    fun getGames(): Flow<List<Game>>
    fun getGamesByDate(date: String): Flow<List<Game>>
    fun getGameById(id: Int): Flow<Game?>
    fun getGamesByTeamId(teamId: Int): Flow<List<Game>>
    suspend fun syncGames()
    suspend fun syncGamesByDate(date: String)
}
```

**关键设计：所有查询方法返回 `Flow`，而不是 suspend 函数。** 这意味着数据是响应式的 — 数据库有更新时，UI 会自动刷新。

### 离线优先实现

```kotlin
internal class OfflineFirstGamesRepository @Inject constructor(
    private val gameDao: GameDao,
    private val networkDataSource: NbaNetworkDataSource,
) : GamesRepository {

    override fun getGamesByDate(date: String): Flow<List<Game>> =
        gameDao.getGamesByDate(date)                          // 1. 从数据库读取
            .map { entities -> entities.map { it.asExternalModel() } }  // 2. 转为领域模型
            .onStart { syncGamesByDate(date) }                // 3. 启动时触发网络同步

    override suspend fun syncGamesByDate(date: String) {
        try {
            val networkGames = networkDataSource.getGames(    // 4. 从网络获取
                perPage = 100, dates = listOf(date)
            )
            val games = networkGames.map { it.asExternalModel() }
            gameDao.upsertGames(games.map { it.asEntity() })  // 5. 写入数据库
        } catch (e: Exception) {
            // 静默失败 — 离线优先意味着展示缓存数据
        }
    }
}
```

**数据流向：**

```
用户请求 → 订阅 Room Flow → Room 返回缓存数据 → UI 立即展示
              ↓
         onStart 触发网络同步
              ↓
         网络返回新数据 → 写入 Room → Room Flow 自动推送更新 → UI 自动刷新
```

这就是 **Single Source of Truth** 原则：UI 永远只从数据库读数据，网络数据先写入数据库再由 Flow 推送。

### DAO 层

```kotlin
@Dao
interface GameDao {
    @Query("SELECT * FROM games WHERE date = :date ORDER BY id")
    fun getGamesByDate(date: String): Flow<List<GameEntity>>

    @Upsert
    suspend fun upsertGames(games: List<GameEntity>)
}
```

使用 `@Upsert` 替代 `@Insert(onConflict = REPLACE)`，这是 Room 的最佳实践 — 存在则更新，不存在则插入。

---

## Navigation 3：类型安全的导航系统

### 为什么不用 Navigation Compose？

Navigation 3 是 Google 最新的导航库（2025 年发布），相比 Navigation Compose 有几个核心优势：

1. **类型安全** — 路由参数通过数据类传递，而非 String
2. **更灵活的 BackStack 管理** — 直接操作 BackStack，无需复杂的 `popUpTo` 配置
3. **与 ViewModel 更好集成** — 内置 `ViewModelStoreNavEntryDecorator`

### NavKey：导航的基石

每个可导航的目的地都定义为一个 `NavKey`：

```kotlin
// 列表页 — 无参数，用 object
@Serializable
object GamesNavKey : NavKey

// 详情页 — 带参数，用 data class
@Serializable
data class GameDetailNavKey(val gameId: Int) : NavKey
```

`@Serializable` 保证了导航参数可以在进程死亡后恢复。

### 双层导航架构

HoopsNow 采用双层导航设计：

```
TopLevelStack（底部导航栏）
├── GamesNavKey ←→ SubStack: [GamesNavKey, GameDetailNavKey(1)]
├── TeamsNavKey ←→ SubStack: [TeamsNavKey, TeamDetailNavKey(5)]
├── PlayersNavKey ←→ SubStack: [PlayersNavKey]
└── FavoritesNavKey ←→ SubStack: [FavoritesNavKey]
```

- **TopLevelStack** — 管理底部导航栏的 Tab 切换
- **SubStack** — 每个 Tab 有自己的子导航栈

```kotlin
class NavigationState(
    val startKey: NavKey,
    val topLevelStack: NavBackStack<NavKey>,
    val subStacks: Map<NavKey, NavBackStack<NavKey>>,
) {
    val currentTopLevelKey: NavKey by derivedStateOf { topLevelStack.last() }
    val currentSubStack: NavBackStack<NavKey>
        get() = subStacks[currentTopLevelKey]!!
    val currentKey: NavKey by derivedStateOf { currentSubStack.last() }
}
```

### Navigator：导航逻辑

```kotlin
class Navigator(val state: NavigationState) {

    fun navigate(key: NavKey) {
        when (key) {
            // 点击当前 Tab → 清空子栈（回到列表页）
            state.currentTopLevelKey -> clearSubStack()
            // 点击其他 Tab → 切换顶层栈
            in state.topLevelKeys -> goToTopLevel(key)
            // 其他 → 推入当前子栈
            else -> goToKey(key)
        }
    }

    fun goBack() {
        when (state.currentKey) {
            state.startKey -> error("Cannot go back from start")
            state.currentTopLevelKey -> {
                // 子栈为空，回到上一个 Tab
                state.topLevelStack.removeLastOrNull()
            }
            else -> state.currentSubStack.removeLastOrNull()
        }
    }

    // 便捷导航方法
    fun navigateToGameDetail(gameId: Int) = navigate(GameDetailNavKey(gameId))
    fun navigateToTeamDetail(teamId: Int) = navigate(TeamDetailNavKey(teamId))
    fun navigateToPlayerDetail(playerId: Int) = navigate(PlayerDetailNavKey(playerId))
}
```

这种设计的优点是：
- 每个 Tab 的导航栈独立保存，切换 Tab 不会丢失状态
- 双击当前 Tab 可以回到顶部（微信同款交互）
- 返回逻辑清晰，不需要 `popUpTo` 这种声明式配置

---

## ViewModel + UiState：单向数据流实践

### UiState 密封接口

每个页面定义一个密封接口来表示所有可能的 UI 状态：

```kotlin
sealed interface GamesUiState {
    data object Loading : GamesUiState
    data object Empty : GamesUiState
    data class Success(val games: List<Game>) : GamesUiState
    data class Error(val message: String) : GamesUiState
}
```

**为什么用 sealed interface 而不是 sealed class？**

- `sealed interface` 允许多继承
- `data object` 比 `object` 更适合作为状态（有正确的 `toString()`）
- 编译器会在 `when` 表达式中检查是否覆盖了所有分支

### ViewModel 实现

```kotlin
@HiltViewModel
class GamesListViewModel @Inject constructor(
    private val gamesRepository: GamesRepository,
) : ViewModel() {

    private val _selectedDateIndex = MutableStateFlow(3) // 今天在中间位置

    @OptIn(ExperimentalCoroutinesApi::class)
    val uiState: StateFlow<GamesUiState> = _selectedDateIndex
        .flatMapLatest { index ->                       // 1. 日期切换触发新的数据流
            val selectedDate = dates[index]
            flow<GamesUiState> {
                emit(GamesUiState.Loading)              // 2. 先发射 Loading
                emitAll(
                    gamesRepository.getGamesByDate(selectedDate)
                        .map { games ->
                            if (games.isEmpty()) GamesUiState.Empty
                            else GamesUiState.Success(games)  // 3. 数据到达后发射 Success
                        }
                        .catch { e ->
                            emit(GamesUiState.Error(e.message ?: "Unknown error"))
                        }
                )
            }
        }
        .stateIn(                                       // 4. 转为 StateFlow
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = GamesUiState.Loading,
        )

    fun selectDate(index: Int) {
        _selectedDateIndex.value = index                // 5. UI 事件向上流动
    }
}
```

**数据流向图：**

```
┌─────────────────────────────────────────────────────┐
│                    Compose UI                        │
│                                                      │
│  collectAsStateWithLifecycle() ← uiState (StateFlow)│
│                                                      │
│  onClick → viewModel.selectDate(index)               │
└─────────────────┬───────────────────────┬───────────┘
                  │ 事件向上               │ 状态向下
┌─────────────────▼───────────────────────▼───────────┐
│                   ViewModel                          │
│                                                      │
│  _selectedDateIndex → flatMapLatest → uiState        │
│                                                      │
│  gamesRepository.getGamesByDate() → map → stateIn    │
└─────────────────────────────────────────────────────┘
```

### Screen 中的状态消费

```kotlin
@Composable
fun GamesListScreen(
    onGameClick: (Int) -> Unit,
    viewModel: GamesListViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        is GamesUiState.Loading -> LoadingScreen()
        is GamesUiState.Empty -> EmptyScreen(message = "No games scheduled")
        is GamesUiState.Error -> ErrorScreen(message = state.message)
        is GamesUiState.Success -> {
            LazyColumn {
                items(state.games, key = { it.id }) { game ->
                    GameCard(
                        game = game,
                        onClick = { onGameClick(game.id) },
                    )
                }
            }
        }
    }
}
```

**关键细节：**

1. `collectAsStateWithLifecycle()` — 生命周期感知的状态收集，Activity 进入后台时自动停止收集，避免浪费资源
2. `key = { it.id }` — 为 LazyColumn 提供稳定的 key，避免不必要的重组
3. `hiltViewModel()` — Hilt 自动创建和管理 ViewModel 实例

### `SharingStarted.WhileSubscribed(5_000)` 的意义

这是 NIA 推荐的 StateFlow 共享策略：

- 有订阅者时开始收集上游 Flow
- 所有订阅者消失后，**等待 5 秒**再停止收集
- 5 秒内如果有新订阅者（比如屏幕旋转），直接复用已有数据

为什么是 5 秒？因为屏幕旋转通常在几秒内完成，5 秒足够覆盖配置变化的窗口期。

---

## Hilt 依赖注入：把一切粘合在一起

### 绑定 Repository

```kotlin
@Module
@InstallIn(SingletonComponent::class)
internal abstract class DataModule {

    @Binds
    @Singleton
    abstract fun bindsGamesRepository(
        impl: OfflineFirstGamesRepository,
    ): GamesRepository

    @Binds
    @Singleton
    abstract fun bindsTeamsRepository(
        impl: OfflineFirstTeamsRepository,
    ): TeamsRepository

    @Binds
    @Singleton
    abstract fun bindsPlayersRepository(
        impl: OfflineFirstPlayersRepository,
    ): PlayersRepository

    @Binds
    @Singleton
    abstract fun bindsFavoritesRepository(
        impl: OfflineFirstFavoritesRepository,
    ): FavoritesRepository
}
```

**设计要点：**

1. `internal abstract class` — 模块内部可见，外部只能看到接口
2. `@Binds` — 比 `@Provides` 更高效，Hilt 在编译期生成绑定代码
3. `@Singleton` — 全局单例，所有 ViewModel 共享同一个 Repository 实例

### ViewModel 注入

```kotlin
@HiltViewModel
class GamesListViewModel @Inject constructor(
    private val gamesRepository: GamesRepository,  // 自动注入接口实现
) : ViewModel()
```

Hilt 看到 `GamesRepository` 参数，会通过 `DataModule` 的绑定找到 `OfflineFirstGamesRepository` 并注入。**ViewModel 完全不知道具体实现是什么。**

这就是依赖倒置原则 (DIP) 的实践 — 高层模块依赖抽象（接口），不依赖具体实现。

---

## 总结与收获

### 架构决策速查表

| 决策 | 选择 | 理由 |
|------|------|------|
| 模块化策略 | feature(api/impl) + core | 编译隔离、松耦合 |
| 构建配置 | Convention Plugins | 消除 build.gradle 重复 |
| 导航方案 | Navigation 3 | 类型安全、灵活的 BackStack |
| 状态管理 | StateFlow + sealed interface | 编译期穷举检查、响应式 |
| 数据策略 | 离线优先 (Room + Retrofit) | 用户体验好、网络容错 |
| 依赖注入 | Hilt | Android 官方推荐 |
| UI 框架 | Jetpack Compose + Material 3 | 声明式 UI、现代设计 |
| 模块依赖引用 | Typesafe Project Accessors | 编译期检查模块路径 |

### NIA 架构的适用场景

**适合：**
- 中大型项目（5+ 功能模块）
- 多人协作团队
- 需要离线支持的应用
- 长期维护的产品

**过度设计的场景：**
- 简单的工具类 App
- 只有 1-2 个页面的 Demo
- 一次性项目

### 从 NIA 学到的核心原则

1. **模块边界即架构边界** — 好的模块划分自然会带来好的架构
2. **Convention over Configuration** — 约定优于配置，Plugin 比文档更可靠
3. **Single Source of Truth** — 一个数据只有一个权威来源（数据库）
4. **响应式 > 命令式** — Flow 比手动调用 `refresh()` 更优雅
5. **编译期 > 运行时** — 类型安全的导航、sealed interface 的穷举检查

### 项目地址

项目已开源，欢迎 Star 和 PR：

**GitHub**: [https://github.com/laibinzhi/hoopsnow](https://github.com/laibinzhi/hoopsnow)

如果这篇文章对你有帮助，欢迎分享给更多 Android 开发者。NIA 架构不是银弹，但它是当前 Android 开发的最佳实践集合，值得每一个 Android 开发者学习和借鉴。
