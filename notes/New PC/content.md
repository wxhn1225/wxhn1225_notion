# New PC

**来源**: 独立页面: New PC

**创建时间**: 2025-06-09T07:09:00.000Z

**最后编辑**: 2025-06-10T14:49:00.000Z

---

> 此页面记录新电脑从0开始的成长过程



## Windows激活

- https://massgrave.dev/（https://github.com/massgravel/Microsoft-Activation-Scripts）


## 代理客户端+机场

- https://jichangtuijian.com/proxyclient.html
- https://www.clashverge.dev/（https://github.com/clash-verge-rev/clash-verge-rev）
- https://free-5620788.webadorsite.com/（https://github.com/DiningFactory/panda-vpn-pro）


## 开发环境

### 📋 环境安装

| 开发 | 环境 |
| --- | --- |
| IDE | VSCode、Cursor |
| Python | PyCharm、Anaconda |
| C++ | CLion、VS、MinGW-win64、CMake |
| Go | GoLand |
| Linux | WSL2（Ubuntu） |
| Docker | Docker Desktop |
| Git | Git、Github Desktop |
| Java | IDEA |
| Remote | Termius、Xshell、Xftp |
| Web | Postman |
| SQL | MySQL、Redis、MongoDB |
| JavaScript | Node.js |

> **说明**: 此数据库内容已同步到 `环境安装/` 文件夹，每行数据对应一个独立的markdown文件

## 社交软件

- https://im.qq.com/index/
- https://weixin.qq.com/
- https://discord.com/
- https://www.dingtalk.com/download
- https://work.weixin.qq.com/nl/sem/registe?from=1011040020&type=1&bd_vid=10991918950830638444
- https://www.feishu.cn/download


## 远程控制

- https://sunlogin.oray.com/
- https://anydesk.com.cn/zhs/downloads/windows


## 游戏

- https://www.wegame.com.cn/home/
- https://store.steampowered.com/about/?l=schinese&pubDate=20250601
- https://shop.battlenet.com.cn/zh-cn


## 录制剪辑

- https://obsproject.com/zh-cn/download
- https://link.bilibili.com/p/eden/download?hotRank=0#/web
- https://www.capcut.cn/
- https://bcut.bilibili.cn/


## 会议

- https://meeting.tencent.com/


## 网盘

- https://pan.baidu.com/disk/main#/index?category=all
- https://www.alipan.com/


## 下载

- https://www.xunlei.com/


## 文档

- https://typora.io/
```shell
@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
 
 
REM 获取当前日期，格式为MM/dd/yyyy
for /f "delims=" %%a in ('wmic OS Get localdatetime ^| find "."') do set datetime=%%a
set "year=!datetime:~0,4!"
set "month=!datetime:~4,2!"
set "day=!datetime:~6,2!"
set "date=!month!/!day!/!year!"
 
REM 设置注册表项
reg add "HKEY_CURRENT_USER\Software\Typora" /v IDate /t REG_SZ /d "!date!" /f > nul
 
 
endlocal
```

- https://www.wps.cn/


