# quark2torrent

夸克网盘批量下载 + 自动制作BT种子的命令行工具。

## 原理

通过Chrome DevTools Protocol (CDP) 从已登录的浏览器获取夸克网盘cookie，调用官方API批量获取文件直链，多线程并行下载后自动生成 `.torrent` 种子文件。

## 前置条件

1. **Chrome浏览器**，以远程调试模式启动：
   ```bash
   # macOS
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

   # Linux
   google-chrome --remote-debugging-port=9222

   # Windows
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```

2. 在打开的Chrome里登录 [pan.quark.cn](https://pan.quark.cn)

3. 安装Python依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### 1. 获取文件夹fid

在夸克网盘里打开目标文件夹，看地址栏：

```
https://pan.quark.cn/list#/list/all/XXXXXXXXXXXXXXXX-文件夹名
                              ^^^^^^^^^^^^^^^^^^^^^^^^ 这一串
```

### 2. 运行

```bash
python3 quark2torrent.py <文件夹fid> <输出目录名>
```

示例：
```bash
python3 quark2torrent.py 5c34ce7f7de24cfca7a771973f69d6f7 叶卡捷琳娜大帝
```

### 3. 结果

- 文件下载到当前目录的 `<输出目录名>/` 文件夹
- 种子文件生成在 `<输出目录名>.torrent`
- 用 qBittorrent / Transmission 打开种子文件即可做种

## 速度

实测单文件8线程并行下载，速度可达 **20-35 MB/s**，52GB约40分钟完成。

## 常见问题

| 问题 | 解决 |
|---|---|
| 找不到夸克标签页 | 先在Chrome里打开并登录 pan.quark.cn |
| 下载返回401/31001 | cookie过期，重新登录夸克网盘 |
| 下载412 | cookie不完整，确认Chrome没有被其他插件干扰 |
| 速度只有100KB/s | 不要修改脚本里的UA配置，保持普通Chrome UA |

## 技术细节

- 下载直链有效期约6-8小时，获取后尽快开始下载
- 脚本自动断点续传，中断后重新运行即可继续
- 支持整个文件夹递归下载，自动保持目录结构
- 内置4个公共Tracker服务器

## License

MIT
