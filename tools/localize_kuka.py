import json,re

IN='apps.json'
OUT='apps.json'
data=json.load(open(IN,encoding='utf-8'))

NAME_MAP={
'微信':'WeChat','QQ':'QQ','多邻国':'Duolingo: Language & Chess','小红书':'rednote','YouTube':'YouTube','YouTube Music':'YouTube Music','X':'X',
'Spotify':'Spotify: Music and Podcasts','WPS Office':'WPS Office-AI Doc, PDF, Sheet','WhatsApp':'WhatsApp Messenger','Telegram':'Telegram Messenger',
'Instagram':'Instagram','Discord':'Discord – Talk, Play, Hang Out','ChatGPT':'ChatGPT','Reddit':'Reddit','Twitch':'Twitch: Live Streaming','Facebook':'Facebook',
'Pinterest':'Pinterest: Lifestyle Ideas','PicsArt':'Picsart AI Photo Editor, Video','PicsArt美易':'Picsart AI Photo Editor, Video','美易-PicsArt':'Picsart AI Photo Editor, Video',
'PS Express':'Photoshop Express Photo Editor','Lightroom':'Lightroom Video & Photo Editor','Adobe Express':'Adobe Express: Create Anything',
'Xmind':'Xmind: AI Mind Map, Brainstorm','QuantumultX':'Quantumult X','Quantumult X':'Quantumult X','支付宝':'Alipay - Simplify Your Life',
'企业微信':'WeCom','剪映国外版':'CapCut: Photo & Video Editor','LINE':'LINE','Snapchat':'Snapchat','pixiv':'pixiv'
}

SPECIAL={
'微信':[
'✅ Bản WeChat tích hợp nhiều plugin, hỗ trợ chạy nhiều bản/tài khoản mà không cần giữ ứng dụng chạy nền.',
'✅ Có các trợ lý/plugin như LaoMao, đấu ảnh, PKC, quản lý plugin và tùy biến giao diện.',
'✅ Hỗ trợ chống thu hồi tin nhắn/WeChat Moments, điều khiển tốc độ video và tự chuyển giọng nói thành văn bản.',
'✅ Có tính năng bạn bè riêng tư và các phím tắt liên quan đến plugin.',
'⚠️ Nguồn Kuka ghi rõ tài nguyên được sưu tầm từ Internet và chỉ dùng để học tập/thử nghiệm.'
],
'QQ':[
'✅ Tích hợp plugin cho QQ; mặc định plugin có thể tắt và người dùng tự bật theo nhu cầu.',
'✅ Hỗ trợ chống thu hồi tin nhắn, lưu ảnh Flash và một số tính năng bổ sung.',
'✅ Phần cài đặt plugin nằm trong giao diện Cài đặt của QQ.',
'⚠️ Nguồn Kuka cảnh báo QQ có cơ chế phát hiện; có rủi ro khóa tài khoản.'
],
'多邻国':[
'✅ Bản Duolingo chỉnh sửa mở khóa tính năng thành viên và không giới hạn tim.',
'✅ Có thể sử dụng các tính năng thành viên, bao gồm nội dung thoại/video nếu phiên bản hỗ trợ.',
'✅ Dùng để học ngoại ngữ; yêu cầu iOS phụ thuộc từng phiên bản trong source.'
],
'小红书':[
'✅ Tích hợp plugin hỗ trợ tải ảnh/video không watermark và loại bỏ phần lớn quảng cáo.',
'✅ Hỗ trợ sao chép tiêu đề/nội dung bằng thao tác nhấn giữ ở một số khu vực.',
'✅ Menu plugin nằm trong phần cài đặt của ứng dụng; cần bật plugin để sử dụng tính năng.'
],
'支付宝':[
'✅ Tích hợp plugin bổ sung cho Alipay.',
'✅ Có tính năng chỉnh số bước và một số tùy chọn bổ sung.',
'✅ Có xử lý nhằm ẩn/bỏ kiểm tra jailbreak.',
'✅ Menu plugin có thể được gọi bằng thao tác nhấn giữ một số khu vực điều hướng theo mô tả nguồn.'
],
'剪映国外版':[
'✅ Bản quốc tế của ứng dụng chỉnh sửa video CapCut.',
'✅ Loại bỏ quảng cáo màn hình khởi động và tích hợp plugin chặn quảng cáo.',
'✅ Nguồn Kuka mô tả bản này có mở khóa tính năng thành viên sau khi đăng nhập.',
'✅ Có thể cài bằng tự ký hoặc TrollStore.'
],
'PicsArt':[
'✅ Bản Picsart chỉnh sửa dành cho chỉnh sửa/làm đẹp ảnh.',
'✅ Đăng nhập để kích hoạt các tính năng thành viên theo mô tả của nguồn.',
'✅ Mở khóa các tính năng nâng cao của ứng dụng.'
],
'PicsArt美易':[
'✅ Bản Picsart chỉnh sửa dành cho chỉnh sửa/làm đẹp ảnh.',
'✅ Đăng nhập để kích hoạt các tính năng thành viên theo mô tả của nguồn.',
'✅ Mở khóa các tính năng nâng cao của ứng dụng.'
],
'美易-PicsArt':[
'✅ Bản Picsart chỉnh sửa dành cho chỉnh sửa/làm đẹp ảnh.',
'✅ Đăng nhập để kích hoạt các tính năng thành viên theo mô tả của nguồn.',
'✅ Mở khóa các tính năng nâng cao của ứng dụng.'
],
'PS Express':[
'✅ Ứng dụng Adobe Photoshop Express dùng để chỉnh sửa ảnh và video.',
'✅ Nguồn Kuka mô tả có thể mở khóa Pro sau khi đăng nhập bằng email/Apple ID mà không cần mua.',
'✅ Mở khóa các tính năng nâng cao và không có cửa sổ quảng cáo bật lên.'
],
'Lightroom':[
'✅ Ứng dụng Adobe Lightroom dùng để chỉnh sửa ảnh và áp dụng preset hàng loạt.',
'✅ Nguồn Kuka mô tả có thể mở khóa Pro sau khi đăng nhập mà không cần mua.',
'✅ Mở khóa các tính năng nâng cao của ứng dụng.'
],
'WPS Office':[
'✅ Bản WPS Office chỉnh sửa mở khóa các tính năng thành viên sau khi đăng nhập.',
'✅ Phần lớn tính năng VIP được mở theo mô tả nguồn.',
'⚠️ Dung lượng lưu trữ đám mây không được mở khóa.'
],
'Telegram':[
'✅ Tích hợp tính năng dịch tự động và tăng tốc tải xuống.',
'✅ Có plugin hỗ trợ bỏ hạn chế chụp màn hình/tải nội dung và loại bỏ quảng cáo theo mô tả nguồn.',
'✅ Menu plugin có thể được gọi bằng thao tác nhấn giữ/ba ngón theo hướng dẫn trong bản Kuka.'
],
'WhatsApp':[
'✅ Có tùy chọn tắt xác nhận đã đọc.',
'✅ Hỗ trợ một số tính năng nhắn tin bổ sung.',
'✅ Có tính năng ẩn tin nhắn và chống thu hồi theo mô tả nguồn.'
],
'Spotify':[
'✅ Bản Spotify chỉnh sửa mở khóa một số tính năng Premium.',
'✅ Hỗ trợ chuyển bài không giới hạn và bỏ chế độ phát ngẫu nhiên bắt buộc.',
'✅ Tích hợp plugin Eevee theo mô tả nguồn.',
'✅ Yêu cầu tối thiểu iOS 16.1 trong phiên bản này.',
'⚠️ Nguồn khuyến cáo giữ khu vực tài khoản phù hợp với máy chủ/VPN đang sử dụng nếu gặp lỗi phát nhạc.'
],
'Discord':[
'✅ Ứng dụng Discord được tích hợp plugin Pyoncord và DiscordNoTrack.',
'✅ Cho phép sử dụng plugin và theme bổ sung theo mô tả nguồn.'
],
'ChatGPT':[
'✅ Bản ứng dụng ChatGPT được nguồn Kuka mô tả là bản chính thức đã giải mã để cài ngoài.',
'✅ Hỗ trợ các tính năng ChatGPT tùy theo tài khoản và dịch vụ OpenAI đang cung cấp.',
'✅ Cần đăng nhập; chất lượng kết nối mạng có thể ảnh hưởng việc sử dụng.',
'✅ Source có các bản cũ dành cho một số phiên bản iOS thấp hơn.'
],
'Reddit':[
'✅ Bản Reddit được tối ưu/chỉnh sửa.',
'✅ Tích hợp plugin RedditFilter để lọc nội dung không mong muốn khỏi feed.'
],
'Twitch':[
'✅ Ứng dụng Twitch chỉnh sửa để giảm/chặn quảng cáo theo mô tả nguồn.',
'✅ Hỗ trợ tải clip, video đầy đủ hoặc nội dung livestream ở một số trường hợp.',
'✅ Có hỗ trợ tải nền và xem ảnh hồ sơ.'
],
'Pinterest':[
'✅ Ứng dụng cộng đồng hình ảnh Pinterest.',
'✅ Nội dung gồm hình nền, nhiếp ảnh, tranh minh họa và nhiều chủ đề khác.',
'✅ Nguồn Kuka mô tả có thể lưu nội dung không quảng cáo/không watermark.',
'✅ Yêu cầu iOS 14 trở lên đối với phiên bản được ghi trong source.'
],
'企业微信':[
'✅ WeCom là công cụ giao tiếp và làm việc dành cho doanh nghiệp của Tencent.',
'✅ Bản Kuka tích hợp plugin trợ lý ảo với một số tính năng như vị trí ảo và mô phỏng Wi‑Fi.',
'✅ Có nhiều thao tác gọi menu plugin bằng nhấn giữ/nhấn nhiều ngón theo mô tả nguồn.',
'⚠️ Nguồn khuyến nghị thử bằng tài khoản phụ vì có thể có rủi ro tài khoản.'
],
'QuantumultX':[
'✅ Quantumult X là công cụ mạng/proxy trên iOS, hỗ trợ module và rewrite.',
'✅ Bản Kuka có chỉnh sửa liên quan đến MITM/rewrite và bỏ một số kiểm tra thiết bị.',
'✅ Nguồn mô tả đây là bản giải mã đầy đủ quyền từ App Store Mỹ.',
'✅ Dành cho TrollStore theo ghi chú nguồn.'
],
'Quantumult X':[
'✅ Quantumult X là công cụ mạng/proxy trên iOS.',
'✅ Phiên bản này được mô tả có hỗ trợ VLESS.',
'✅ Nguồn ghi chú bản này dành cho TrollStore.'
],
'Adobe Express':[
'✅ Adobe Express dùng để tạo logo, poster, thiệp và nội dung đồ họa.',
'✅ Bản Kuka mô tả có mở khóa các tính năng thành viên cao cấp.'
],
'Xmind':[
'✅ Xmind là ứng dụng sơ đồ tư duy và tổ chức ý tưởng.',
'✅ Các tính năng mở khóa phụ thuộc phiên bản Kuka đang cung cấp.'
],
'X':[
'✅ Bản X/Twitter được tích hợp plugin BHTwitter.',
'✅ Có các tính năng bổ sung như vị trí ảo, dịch và tùy chỉnh theo plugin.',
'✅ Yêu cầu iOS 15 trở lên theo mô tả nguồn.'
],
'TikTok':[
'✅ Bản TikTok được tích hợp plugin để tải video, giảm quảng cáo và bổ sung các tùy chọn phát.',
'✅ Có thể hỗ trợ chuyển khu vực và một số tùy chỉnh giao diện/tính năng theo plugin.',
'⚠️ Khả năng đăng nhập và tính năng có thể phụ thuộc phiên bản, khu vực và plugin.'
],
'YouTube':[
'✅ Bản YouTube được tích hợp plugin YTKACE và các plugin bổ sung.',
'✅ Hỗ trợ tải video, giảm quảng cáo, Picture‑in‑Picture và một số tính năng nâng cao.',
'✅ Yêu cầu iOS 16 trở lên theo mô tả nguồn.'
],
'YouTube Music':[
'✅ Bản YouTube Music có các chỉnh sửa/tính năng bổ sung theo nguồn Kuka.',
'✅ Khả năng phát nền, quảng cáo và tải xuống phụ thuộc plugin/phiên bản.'
],
'Facebook':[
'✅ Bản Facebook có các chỉnh sửa/tính năng bổ sung theo nguồn Kuka.',
'✅ Chi tiết phụ thuộc plugin và phiên bản được cung cấp.'
],
'Instagram':[
'✅ Bản Instagram có các chỉnh sửa/tính năng bổ sung theo nguồn Kuka.',
'✅ Các chức năng thường liên quan đến tải nội dung, quảng cáo hoặc quyền riêng tư tùy phiên bản.'
]
}

FEATURES=[
(r'解锁.*?(会员|VIP|SVIP|Pro|高级|专业版)|破解会员|永久会员','✅ Mở khóa tính năng thành viên/VIP/Pro.'),
(r'内购|无限购买|随意充值|充值','✅ Có chỉnh sửa liên quan đến mua hàng trong ứng dụng/tài nguyên trả phí.'),
(r'去.*广告|无广告|广告加速|屏蔽广告','✅ Có chỉnh sửa để giảm, chặn hoặc bỏ qua quảng cáo.'),
(r'水印','✅ Có tính năng liên quan đến loại bỏ/lưu nội dung không watermark.'),
(r'下载|导出','✅ Có tính năng tải xuống hoặc xuất nội dung.'),
(r'无限金币','✅ Không giới hạn tiền vàng.'),
(r'无限钻石','✅ Không giới hạn kim cương.'),
(r'无限.*(货币|钱币|资源|宝石)','✅ Không giới hạn một số loại tiền/tài nguyên trong game.'),
(r'无限体力','✅ Thể lực không giới hạn.'),
(r'无限.*(子弹|弹药)','✅ Đạn/đạn dược không giới hạn.'),
(r'无限.*(技能|能量|生命|红心)','✅ Không giới hạn một số chỉ số như kỹ năng, năng lượng, sinh lực hoặc tim.'),
(r'无敌|免伤','✅ Có chế độ bất tử/miễn sát thương.'),
(r'一击必杀|秒杀','✅ Có tính năng tăng sát thương/tiêu diệt nhanh.'),
(r'加速','✅ Có tính năng tăng tốc.'),
(r'防撤回','✅ Có tính năng chống thu hồi nội dung/tin nhắn.'),
(r'虚拟定位|更改定位|更改位置','✅ Có tính năng vị trí ảo/thay đổi vị trí GPS.'),
(r'翻译','✅ Có tính năng dịch.'),
(r'播放器|播放','✅ Có tính năng phát nội dung đa phương tiện.'),
(r'照片|相机|修图|图片','✅ Có tính năng liên quan đến ảnh/chỉnh sửa ảnh.'),
(r'视频|影视','✅ Có tính năng liên quan đến video/phim.'),
(r'音乐|歌曲|音质','✅ Có tính năng liên quan đến âm nhạc/chất lượng âm thanh.'),
(r'漫画|动漫|番剧','✅ Có nội dung/tính năng liên quan đến truyện tranh hoặc anime.'),
(r'阅读|小说|书源','✅ Có tính năng đọc sách/tiểu thuyết hoặc đổi nguồn nội dung.'),
(r'代理|VPN|节点|vless|MITM|重写','✅ Có tính năng mạng/VPN/proxy hoặc tùy chỉnh lưu lượng.'),
(r'插件','✅ Có tích hợp plugin bổ sung.'),
(r'多开','✅ Hỗ trợ nhân bản/chạy nhiều tài khoản hoặc nhiều bản ứng dụng.'),
(r'砸壳|付费游戏|付费软件','✅ Nguồn mô tả đây là ứng dụng/game trả phí hoặc bản đã giải mã để cài ngoài App Store.'),
(r'巨魔|Troll','✅ Có ghi chú liên quan đến TrollStore.'),
(r'越狱','✅ Có ghi chú hoặc xử lý liên quan đến jailbreak.'),
(r'iOS\s*\d+(?:\.\d+)?','✅ Có yêu cầu phiên bản iOS cụ thể; xem số phiên bản trong metadata.'),
(r'登录|登陆','✅ Có yêu cầu/lưu ý liên quan đến đăng nhập.'),
(r'封号','⚠️ Có cảnh báo rủi ro khóa tài khoản.'),
(r'资源来自网络|仅供学习|仅用于学习|测试交流','⚠️ Nguồn Kuka ghi chú tài nguyên chỉ dành cho học tập/thử nghiệm.'),
(r'下架','⚠️ Ứng dụng có thể đã bị gỡ hoặc có nguy cơ bị gỡ khỏi App Store.')
]

TYPE_HINTS=[
(r'相机','Ứng dụng máy ảnh/chỉnh sửa hình ảnh.'),
(r'壁纸','Ứng dụng hình nền/chủ đề.'),
(r'日历|万年历','Ứng dụng lịch/tiện ích ngày tháng.'),
(r'浏览器','Trình duyệt web.'),
(r'输入法','Bàn phím/phương thức nhập liệu.'),
(r'收音机','Ứng dụng radio.'),
(r'健身|训练','Ứng dụng hỗ trợ tập luyện/thể thao.'),
(r'游戏模拟器|模拟器','Trình giả lập game/hệ máy.'),
(r'媒体播放器','Trình phát đa phương tiện.')
]

ASCII_TECH=re.compile(r'\b(?:iOS\s*\d+(?:\.\d+)*(?:\+)?|[A-Za-z][A-Za-z0-9+_.-]{2,})\b')

def generic_desc(old_name, desc):
    d=desc or ''
    out=[]
    for pat,text in TYPE_HINTS:
        if re.search(pat,d) and ('✅ '+text) not in out: out.append('✅ '+text)
    for pat,text in FEATURES:
        if re.search(pat,d,re.I) and text not in out: out.append(text)
    toks=[]
    for t in ASCII_TECH.findall(d):
        t=t.strip()
        if t.lower() in {'app','store','vip','pro','ios'}: continue
        if t not in toks: toks.append(t)
    if toks:
        out.append('ℹ️ Tên kỹ thuật/plugin được nhắc trong nguồn: ' + ', '.join(toks[:5]) + '.')
    if not out:
        out=['✅ Bản ứng dụng được nguồn Kuka lưu trữ/chỉnh sửa; mô tả gốc không đủ rõ để dịch chi tiết mà không suy đoán.']
    return '\n'.join(out)

def localize(old_name, desc):
    return '\n'.join(SPECIAL[old_name]) if old_name in SPECIAL else generic_desc(old_name,desc)

renamed=0
for a in data.get('apps',[]):
    old=a.get('name','')
    desc=a.get('localizedDescription') or a.get('versionDescription') or ''
    vi=localize(old,desc)
    if old in NAME_MAP:
        if a['name']!=NAME_MAP[old]: renamed+=1
        a['name']=NAME_MAP[old]
    a['localizedDescription']=vi
    a['versionDescription']=vi
    a['subtitle']='Có liên kết tải từ nguồn Kuka' if a.get('downloadURL') else 'Kuka chưa công khai liên kết tải cho mục này'
    for v in a.get('versions') or []:
        v['localizedDescription']=vi

for n in data.get('news') or []:
    n['caption']='Nguồn Kuka: nội dung/tài nguyên chỉ dành cho học tập và thử nghiệm. Vui lòng tuân thủ điều khoản, bản quyền và pháp luật áp dụng.'

data['name']='Kuka Source for Feather - Vietnamese'
data['description']='Danh mục Kuka cho Feather. Mô tả đã được Việt hóa; tên app chỉ chuẩn hóa khi đối chiếu chắc chắn với App Store.'

bad=[]
url_re=re.compile(r'^https?://',re.I)
for i,a in enumerate(data['apps']):
    if not a.get('name'): bad.append((i,'name'))
    if not a.get('iconURL') or not url_re.match(a['iconURL']): bad.append((i,'iconURL'))
    if a.get('downloadURL')=='': bad.append((i,'downloadURL-empty'))
    if 'downloadURL' in a and a['downloadURL'] is not None and a['downloadURL'] and not url_re.match(a['downloadURL']): bad.append((i,'downloadURL-invalid'))
    if re.search(r'[\u3400-\u9fff]',a.get('localizedDescription','')): bad.append((i,'Chinese-description'))
    for v in a.get('versions') or []:
        if v.get('downloadURL')=='': bad.append((i,'version-downloadURL-empty'))
        if re.search(r'[\u3400-\u9fff]',v.get('localizedDescription','')): bad.append((i,'Chinese-version-description'))

if bad:
    raise SystemExit('QA failed: '+repr(bad[:20]))

with open(OUT,'w',encoding='utf-8') as f:
    json.dump(data,f,ensure_ascii=False,indent=2)

print(f'Localized {len(data["apps"])} apps; renamed {renamed}; QA OK')
