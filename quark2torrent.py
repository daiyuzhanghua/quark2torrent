#!/usr/bin/env python3
"""
quark2torrent - 夸克网盘批量下载并制作BT种子

用法:
  python3 quark2torrent.py <文件夹fid> <输出目录名>

示例:
  python3 quark2torrent.py 5c34ce7f7de24cfca7a771973f69d6f7 叶卡捷琳娜大帝
"""
import json, os, sys, time, threading, urllib.request, urllib.error

# ============ 配置 ============
CDP_HTTP = "http://127.0.0.1:9222"
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
DOWNLOAD_THREADS = 8
TRACKERS = [
    ['udp://tracker.opentrackr.org:1337/announce'],
    ['udp://tracker.openbittorrent.com:80/announce'],
    ['udp://tracker.torrent.eu.org:451/announce'],
]
# ==============================


def get_cookie():
    """通过CDP从浏览器获取夸克cookie"""
    import websocket
    tabs = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5).read())
    tab = next((t for t in tabs if t['type'] == 'page' and 'pan.quark.cn' in t.get('url', '')), None)
    if not tab:
        print("错误: 浏览器中没有打开 pan.quark.cn，请先在浏览器登录夸克网盘")
        sys.exit(1)
    ws = websocket.create_connection(tab['webSocketDebuggerUrl'], timeout=10, origin="http://127.0.0.1:8081")
    ws.send(json.dumps({'id': 1, 'method': 'Network.getAllCookies'}))
    data = json.loads(ws.recv())
    ws.close()
    cookies = [c for c in data['result']['cookies'] if 'quark.cn' in c.get('domain', '')]
    return '; '.join(f"{c['name']}={c['value']}" for c in cookies)


def api(path, cookie, method='GET', data=None):
    url = f"https://drive-pc.quark.cn/1/clouddrive{path}"
    headers = {'Cookie': cookie, 'User-Agent': UA_BROWSER, 'Accept': 'application/json'}
    body = json.dumps(data).encode() if data else None
    if body:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def list_all_files(root_fid, cookie):
    """递归遍历所有文件"""
    files = []
    def walk(fid, path):
        d = api(f"/file/sort?pr=ucpro&fr=pc&pdir_fid={fid}&_page=1&_size=200", cookie)
        if d.get('code') != 0:
            print(f"  警告: 列出目录失败 {d.get('message','')}")
            return
        for item in d['data']['list']:
            full = f"{path}/{item['file_name']}" if path else item['file_name']
            if item.get('dir'):
                walk(item['fid'], full)
            else:
                files.append({'fid': item['fid'], 'path': full, 'size': item['size']})
    walk(root_fid, '')
    return files


def get_download_urls(fids, cookie):
    """批量获取下载直链"""
    result = {}
    for i in range(0, len(fids), 50):
        batch = fids[i:i+50]
        d = api("/file/download?pr=ucpro&fr=pc", cookie, 'POST', {'fids': batch})
        if d.get('code') == 0:
            for item in d['data']:
                result[item['fid']] = item['download_url']
        else:
            print(f"  警告: 获取直链失败 {d.get('message','')}")
    return result


def download_chunk(url, start, end, filepath, idx, results):
    """下载一个文件块"""
    tmp = f"{filepath}.part{idx}"
    existing = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    if existing >= end - start + 1:
        results[idx] = True
        return
    req = urllib.request.Request(url, headers={
        'User-Agent': UA_BROWSER,
        'Range': f'bytes={start+existing}-{end}'
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, 'ab') as f:
            while True:
                chunk = r.read(1024*1024)
                if not chunk:
                    break
                f.write(chunk)
        results[idx] = True
    except Exception as e:
        results[idx] = False


def download_file(url, filepath, size):
    """多线程下载单个文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath) and os.path.getsize(filepath) == size:
        return True
    chunk_size = size // DOWNLOAD_THREADS
    results = {}
    threads = []
    for i in range(DOWNLOAD_THREADS):
        s = i * chunk_size
        e = (i+1)*chunk_size - 1 if i < DOWNLOAD_THREADS-1 else size-1
        t = threading.Thread(target=download_chunk, args=(url, s, e, filepath, i, results))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    if not all(results.get(i) for i in range(DOWNLOAD_THREADS)):
        return False
    with open(filepath, 'wb') as out:
        for i in range(DOWNLOAD_THREADS):
            with open(f"{filepath}.part{i}", 'rb') as f:
                out.write(f.read())
            os.remove(f"{filepath}.part{i}")
    return os.path.getsize(filepath) == size


def make_torrent(folder_path, output_name):
    from torrentool.api import Torrent
    t = Torrent.create_from(folder_path)
    t.announce_urls = TRACKERS
    t.comment = "Created by quark2torrent"
    t.to_file(output_name)
    return os.path.getsize(output_name), t.total_size, t.info_hash


def main():
    if len(sys.argv) < 3:
        print("用法: python3 quark2torrent.py <文件夹fid> <输出目录名>")
        print("示例: python3 quark2torrent.py 5c34ce7f7de24cfca7a771973f69d6f7 叶卡捷琳娜大帝")
        sys.exit(1)

    root_fid = sys.argv[1]
    out_dir = sys.argv[2]

    print("[1/4] 获取登录cookie...")
    cookie = get_cookie()
    print(f"      OK, cookie长度 {len(cookie)}")

    print("[2/4] 遍历文件列表...")
    files = list_all_files(root_fid, cookie)
    total = sum(f['size'] for f in files)
    print(f"      共 {len(files)} 个文件, 总计 {total/1024/1024/1024:.1f} GB")

    print("[3/4] 获取下载直链...")
    urls = get_download_urls([f['fid'] for f in files], cookie)
    print(f"      成功获取 {len(urls)} 个直链")

    print("[4/4] 多线程下载...")
    for i, f in enumerate(files):
        if f['fid'] not in urls:
            print(f"      跳过(无直链): {f['path']}")
            continue
        filepath = os.path.join(out_dir, f['path'])
        print(f"      [{i+1}/{len(files)}] {f['path']} ({f['size']/1024/1024:.0f}MB)")
        for attempt in range(3):
            if download_file(urls[f['fid']], filepath, f['size']):
                break
            time.sleep(2)

    print("\n制作BT种子...")
    torrent_name = f"{out_dir}.torrent"
    tsize, ttotal, ihash = make_torrent(out_dir, torrent_name)
    print(f"完成! 种子文件: {torrent_name} ({tsize/1024:.0f} KB)")
    print(f"总大小: {ttotal/1024/1024/1024:.1f} GB")
    print(f"Info Hash: {ihash}")


if __name__ == '__main__':
    main()
