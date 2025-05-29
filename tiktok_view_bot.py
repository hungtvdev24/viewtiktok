import datetime
import random
import requests
import re
import threading
import time
from hashlib import md5
from time import time as T
import secrets
from concurrent.futures import ThreadPoolExecutor
import json
import gc  # Thêm garbage collection


class Signature:
    def __init__(self, params: str, data: str, cookies: str) -> None:
        self.params = params
        self.data = data
        self.cookies = cookies


    def hash(self, data: str) -> str:
        return str(md5(data.encode()).hexdigest())


    def calc_gorgon(self) -> str:
        gorgon = self.hash(self.params)
        if self.data:
            gorgon += self.hash(self.data)
        else:
            gorgon += str("0"*32)
        if self.cookies:
            gorgon += self.hash(self.cookies)
        else:
            gorgon += str("0"*32)
        gorgon += str("0"*32)
        return gorgon


    def get_value(self):
        gorgon = self.calc_gorgon()
        return self.encrypt(gorgon)


    def encrypt(self, data: str):
        unix = int(T())
        len = 0x14
        key = [
            0xDF, 0x77, 0xB9, 0x40, 0xB9, 0x9B, 0x84, 0x83,
            0xD1, 0xB9, 0xCB, 0xD1, 0xF7, 0xC2, 0xB9, 0x85,
            0xC3, 0xD0, 0xFB, 0xC3,
        ]


        param_list = []
        for i in range(0, 12, 4):
            temp = data[8 * i : 8 * (i + 1)]
            for j in range(4):
                H = int(temp[j * 2 : (j + 1) * 2], 16)
                param_list.append(H)


        param_list.extend([0x0, 0x6, 0xB, 0x1C])


        H = int(hex(unix), 16)
        param_list.append((H & 0xFF000000) >> 24)
        param_list.append((H & 0x00FF0000) >> 16)
        param_list.append((H & 0x0000FF00) >> 8)
        param_list.append((H & 0x000000FF) >> 0)


        eor_result_list = []
        for A, B in zip(param_list, key):
            eor_result_list.append(A ^ B)


        for i in range(len):
            C = self.reverse(eor_result_list[i])
            D = eor_result_list[(i + 1) % len]
            E = C ^ D
            F = self.rbit(E)
            H = ((F ^ 0xFFFFFFFF) ^ len) & 0xFF
            eor_result_list[i] = H


        result = ""
        for param in eor_result_list:
            result += self.hex_string(param)


        return {"X-Gorgon": ("840280416000" + result), "X-Khronos": str(unix)}


    def rbit(self, num):
        result = ""
        tmp_string = bin(num)[2:]
        while len(tmp_string) < 8:
            tmp_string = "0" + tmp_string
        for i in range(0, 8):
            result = result + tmp_string[7 - i]
        return int(result, 2)


    def hex_string(self, num):
        tmp_string = hex(num)[2:]
        if len(tmp_string) < 2:
            tmp_string = "0" + tmp_string
        return tmp_string


    def reverse(self, num):
        tmp_string = self.hex_string(num)
        return int(tmp_string[1:] + tmp_string[:1], 16)


# Danh sách proxy để xoay (rotating proxy)
proxy_list = []
def load_proxies():
    global proxy_list
    try:
        with open('proxy.txt', 'r', encoding='utf8') as f:
            proxy_lines = [line.strip() for line in f.readlines() if line.strip()]
            proxy_list = []
            for proxy_line in proxy_lines:
                if ':' in proxy_line:
                    ip, port = proxy_line.split(':')
                    proxy = {
                        "http": f"http://{ip}:{port}",
                        "https": f"http://{ip}:{port}"
                    }
                    proxy_list.append(proxy)
                else:
                    proxy_list.append(None)
        if not proxy_list:
            proxy_list = [None]
    except Exception as e:
        print(f'[-] Lỗi khi tải proxy: {e}')
        proxy_list = [None]


# Hàm chọn proxy ngẫu nhiên
def selec_proxy():
    return random.choice(proxy_list)


# Hàm xử lý phản hồi
def handle_response(resp: dict):
    first_key = next(iter(resp), None)
    if first_key == 'status_code' and resp.get('status_code') == 0:
        extra = resp.get('extra', {})
        log_pb = resp.get('log_pb', {})
        if 'now' in extra and 'impr_id' in log_pb:
            return True
    return False


# Hàm gửi view
def send_view(start_time, stop_event):
    global count
    url_view = 'https://api16-core-c-alisg.tiktokv.com/aweme/v1/aweme/stats/?ac=WIFI&op_region=VN'
    max_retries = 3
    while not stop_event.is_set():
        if time.time() - start_time > 15:  # Chu kỳ 15 giây
            print("[+] Đã chạy 15 giây, dừng luồng để reset...")
            break


        proxy = selec_proxy()  # Chọn proxy ngẫu nhiên


        random_hex = secrets.token_hex(16)
        headers_view = {
            'Host': 'api16-core-c-alisg.tiktokv.com',
            'Content-Length': '138',
            'Sdk-Version': '2',
            'Passport-Sdk-Version': '5.12.1',
            'X-Tt-Token': f'01{random_hex}0263ef2c096122cc1a97dec9cd12a6c75d81d3994668adfbb3ffca278855dd15c8056ad18161b26379bbf95d25d1f065abd5dd3a812f149ca11cf57e4b85ebac39d - 1.0.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'TikTok 37.0.4 rv:174014 (iPhone; iOS 14.2; ar_SA@calendar=gregorian) Cronet',
            'X-Ss-Stub': '727D102356930EE8C1F61B112F038D96',
            'X-Tt-Store-Idc': 'alisg',
            'X-Tt-Store-Region': 'sa',
            'X-Ss-Dp': '1233',
            'X-Tt-Trace-Id': '00-33c8a619105fd09f13b65546057d04d1-33c8a619105fd09f-01',
            'Accept-Encoding': 'gzip, deflate',
            'X-Khronos': '',
            'X-Gorgon': '',
            'X-Common-Params-V2': (
                "pass-region=1&pass-route=1"
                "&language=ar"
                "&version_code=17.4.0"
                "&app_name=musical_ly"
                "&vid=0F62BF08-8AD6-4A4D-A870-C098F5538A97"
                "&app_version=17.4.0"
                "&carrier_region=VN"
                "&channel=App%20Store"
                "&mcc_mnc=45201"
                "&device_id=6904193135771207173"
                "&tz_offset=25200"
                "&account_region=VN"
                "&sys_region=VN"
                "&aid=1233"
                "&residence=VN"
                "&screen_width=1125"
                "&uoo=1"
                "&openudid=c0c519b4e8148dec69410df9354e6035aa155095"
                "&os_api=18"
                "&os_version=14.2"
                "&app_language=ar"
                "&tz_name=Asia%2FHo_Chi_Minh"
                "¤t_region=VN"
                "&device_platform=iphone"
                "&build_number=174014"
                "&device_type=iPhone14,6"
                "&iid=6958149070179878658"
                "&idfa=00000000-0000-0000-0000-000000000000"
                "&locale=ar"
                "&cdid=D1D404AE-ABDF-4973-983C-CC723EA69906"
                "&content_language="
            ),
        }
        cookie_view = {'sessionid': random_hex}
        start = datetime.datetime(2020, 1, 1, 0, 0, 0)
        end = datetime.datetime(2024, 12, 31, 23, 59, 59)
        delta_seconds = int((end - start).total_seconds())
        random_offset = random.randint(0, delta_seconds)
        random_dt = start + datetime.timedelta(seconds=random_offset)
        data = {
            'action_time': int(time.time()),
            'aweme_type': 0,
            'first_install_time': int(random_dt.timestamp()),
            'item_id': video_id,
            'play_delta': 1,
            'tab_type': 4
        }
        retries = 0
        while retries < max_retries and not stop_event.is_set():
            try:
                sig = Signature(params='ac=WIFI&op_region=VN', data=str(data), cookies=str(cookie_view)).get_value()
                headers_view['X-Khronos'] = sig['X-Khronos']
                headers_view['X-Gorgon'] = sig['X-Gorgon']
                r = requests.post(url_view, data=data, headers=headers_view, cookies=cookie_view, proxies=proxy, timeout=10)
                response = r.json()
                print(f"[+] Gửi view thành công: {response}")
                if handle_response(response):
                    count += 1
                    print(f"[+] Tổng số view: {count}")
                time.sleep(random.uniform(0.5, 2))
                break
            except Exception as e:
                print(f'[-] Lỗi khi gửi view: {e}')
                retries += 1
                time.sleep(1)
        if retries >= max_retries:
            print(f'[-] Đã thử {max_retries} lần nhưng thất bại, tạm dừng luồng này')
            time.sleep(3)


# Hàm lấy video ID từ link
def get_video_id(link):
    headers_id = {
        'Connection': 'close',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
        'Accept': 'text/html'
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            session = requests.Session()
            response = session.get(link, headers=headers_id, timeout=10, allow_redirects=True)
            final_url = response.url
            print(f"[+] Link đầy đủ: {final_url}")


            page = requests.get(final_url, headers=headers_id, timeout=10).text
            match = re.search(r'"video":\{"id":"(\d+)"', page)
            if match:
                video_id = match.group(1)
                print(f'[+] Lấy ID Video thành công: {video_id}')
                return video_id
            else:
                print('[-] Không tìm thấy ID Video')
                return None
        except Exception as e:
            print(f'[-] Lỗi khi lấy ID Video (thử {attempt + 1}/{max_retries}): {e}')
            time.sleep(1)
    return None


# Hàm đọc hoặc ghi link vào file data.txt
def manage_link():
    data_file = 'data.txt'


    # Hàm đọc danh sách link từ file
    def load_links():
        try:
            with open(data_file, 'r', encoding='utf8') as f:
                data = json.load(f)
                return data.get('links', [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []


    # Hàm lưu danh sách link vào file
    def save_links(links):
        with open(data_file, 'w', encoding='utf8') as f:
            json.dump({'links': links}, f, indent=4)


    # Hàm tạo ID mới (STT) dựa trên danh sách hiện tại
    def get_next_id(links):
        if not links:
            return 1
        max_id = max(link.get('id', 0) for link in links)
        return max_id + 1


    # Đọc danh sách link hiện tại
    links = load_links()


    while True:
        print("\n=== QUẢN LÝ LINK VIDEO TIKTOK ===")
        print("1. Chạy với link có sẵn")
        print("2. Thêm link mới")
        print("3. Xóa link")
        print("4. Thoát")
        choice = input("Chọn một tùy chọn (1-4): ").strip()


        if choice == '1':
            if not links:
                print("[-] Chưa có link nào trong danh sách!")
                new_url = input("Nhập link video TikTok mới: ").strip().strip('"').strip("'")
                new_title = input("Nhập tiêu đề cho link: ").strip()
                if new_url and new_title:
                    new_id = get_next_id(links)
                    links.append({"id": new_id, "url": new_url, "title": new_title})
                    save_links(links)
                    print(f"[+] Đã thêm link: {new_url} (STT: {new_id}, Tiêu đề: {new_title})")
                    return new_url
                else:
                    print("[-] Link hoặc tiêu đề không hợp lệ, thử lại.")
                    continue


            print("\nDanh sách link hiện tại:")
            for link in links:
                print(f"STT: {link['id']} | Tiêu đề: {link['title']} | URL: {link['url']}")
            try:
                selected_id = int(input("Nhập STT của link để chạy: "))
                selected_link = next((link for link in links if link['id'] == selected_id), None)
                if selected_link:
                    print(f"[+] Đã chọn: {selected_link['title']} ({selected_link['url']})")
                    return selected_link['url']
                else:
                    print("[-] STT không hợp lệ!")
            except ValueError:
                print("[-] Vui lòng nhập STT hợp lệ!")


        elif choice == '2':
            new_url = input("Nhập link video TikTok mới: ").strip().strip('"').strip("'")
            new_title = input("Nhập tiêu đề cho link: ").strip()
            if new_url and new_title and not any(link['url'] == new_url for link in links):
                new_id = get_next_id(links)
                links.append({"id": new_id, "url": new_url, "title": new_title})
                save_links(links)
                print(f"[+] Đã thêm link: {new_url} (STT: {new_id}, Tiêu đề: {new_title})")
            else:
                print("[-] Link không hợp lệ, đã tồn tại, hoặc tiêu đề rỗng!")


        elif choice == '3':
            if not links:
                print("[-] Chưa có link nào để xóa!")
                continue
            print("\nDanh sách link hiện tại:")
            for link in links:
                print(f"STT: {link['id']} | Tiêu đề: {link['title']} | URL: {link['url']}")
            try:
                selected_id = int(input("Nhập STT của link để xóa: "))
                selected_link = next((link for link in links if link['id'] == selected_id), None)
                if selected_link:
                    confirm = input(f"Bạn có chắc chắn muốn xóa link '{selected_link['title']}' (STT: {selected_id})? [y/n]: ").strip().lower()
                    if confirm == 'y':
                        links.remove(selected_link)
                        save_links(links)
                        print(f"[+] Đã xóa link: {selected_link['url']} (STT: {selected_id}, Tiêu đề: {selected_link['title']})")
                    else:
                        print("[+] Hủy xóa link.")
                else:
                    print("[-] STT không hợp lệ!")
            except ValueError:
                print("[-] Vui lòng nhập STT hợp lệ!")


        elif choice == '4':
            print("[-] Thoát chương trình.")
            exit()


        else:
            print("[-] Tùy chọn không hợp lệ, vui lòng chọn lại!")


# Vòng lặp chính để chạy lại tự động với link từ file
def main():
    global count, video_id
    # Tải proxy trước khi chạy
    load_proxies()


    # Lấy link từ file hoặc nhập lần đầu
    link = manage_link()


    max_attempts = 5
    attempt = 0
    cycle_count = 0


    while attempt < max_attempts:
        cycle_start_time = time.time()
        count = 0


        # Lấy ID video từ link
        video_id = get_video_id(link)
        if not video_id:
            print(f"[-] Không thể lấy video ID, thử lại (lần {attempt + 1}/{max_attempts})...")
            attempt += 1
            time.sleep(1)
            continue
        attempt = 0


        # Khởi tạo và chạy các luồng với ThreadPoolExecutor
        stop_event = threading.Event()
        start_time = time.time()
        total_threads = 50000
        max_workers = 5000
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(send_view, start_time, stop_event) for _ in range(total_threads)]


            # Đợi 15 giây
            time.sleep(15)
            stop_event.set()


        # Đợi các luồng thoát hoàn toàn
        time.sleep(5)
        print("[+] Resetting program after 15 seconds...")


        # Dọn dẹp tài nguyên
        gc.collect()


        # Giám sát hiệu suất
        cycle_count += 1
        cycle_duration = time.time() - cycle_start_time
        print(f"[+] Chu kỳ {cycle_count} hoàn thành trong {cycle_duration:.2f} giây, gửi được {count} view.")


    if attempt >= max_attempts:
        print("[-] Đã thử tối đa lần nhưng thất bại, thoát chương trình...")


if __name__ == "__main__":
    main()

