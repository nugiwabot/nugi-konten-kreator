import os
import json
import urllib.request
import urllib.parse
import time

MCP_URL = "https://mcp.pexafy.com/mcp"
def get_pexafy_token():
    token = os.environ.get("PEXAFY_API_KEY")
    if token:
        return token
    config_path = os.path.expanduser(r"~/.gemini/config/mcp_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                auth = data.get("mcpServers", {}).get("pexafy", {}).get("headers", {}).get("Authorization", "")
                if auth.startswith("Bearer "):
                    return auth.split("Bearer ")[1].strip()
                return auth.strip()
        except Exception:
            pass
    return ""

TOKEN = get_pexafy_token()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/event-stream"
}

def init_mcp_session():
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pexafy-narasi-downloader-part2", "version": "1.0"}
        }
    }
    req = urllib.request.Request(MCP_URL, data=json.dumps(init_payload).encode("utf-8"), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req) as resp:
        session_id = resp.headers.get("mcp-session-id")
    print(f"MCP Session Initialized: {session_id}")
    return session_id

def search_photos(session_id, query, orientation="portrait"):
    headers = dict(HEADERS)
    if session_id:
        headers["mcp-session-id"] = session_id
        
    call_payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000) % 100000,
        "method": "tools/call",
        "params": {
            "name": "search_photos",
            "arguments": {
                "q": query,
                "orientation": orientation
            }
        }
    }
    req = urllib.request.Request(MCP_URL, data=json.dumps(call_payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        for line in resp.read().decode("utf-8").splitlines():
            if line.startswith("data: "):
                res = json.loads(line[6:])
                text_content = res.get("result", {}).get("content", [{}])[0].get("text", "{}")
                parsed = json.loads(text_content)
                return parsed.get("data", [])
    return []

def download_image(url, target_path):
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
    with open(target_path, "wb") as f:
        f.write(content)
    return len(content)

NARASI_PLANS_PART2 = [
    {
        "id": "narasi-06",
        "title": "Mengapa Anak yang Terlalu Cepat Diajari AI Berisiko Kehilangan Daya Pikirnya?",
        "pillar": "AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-06",
        "scenes": [
            {
                "file_name": "01_hook_child_with_ai_tablet.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Banyak orang tua bangga banget pas ngeliat anaknya yang masih SD udah jago pakai AI buat ngerjain PR dan bikin tugas sekolah.",
                "visual_concept": "Anak SD memegang tablet digital belajar dengan teknologi di ruang belajar modern",
                "search_query": "elementary school child sitting with digital tablet laptop studying modern technology classroom",
                "b_roll_cue": "Cut dari talking head saat menyebut 'bangga lihat anak SD pakai AI'. Tampilkan anak kecil asyik menatap layar tablet."
            },
            {
                "file_name": "02_tension_instant_screen_glow.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Kelihatannya keren dan melek teknologi. Tapi kalau kita amati riset perkembangan otak anak, kebiasaan mendapatkan jawaban instan dalam lima detik justru diam-diam mematikan satu kemampuan paling mendasar manusia.",
                "visual_concept": "Wajah anak terpapar cahaya biru layar gadget dalam kegelapan",
                "search_query": "close up kid child face illuminated by glowing screen in dark looking captivated",
                "b_roll_cue": "Close up dramatis mata anak memantulkan cahaya dingin layar gadget."
            },
            {
                "file_name": "03_data_child_math_struggle.jpg",
                "timestamp": "[00:18 - 00:29] CONTEXT & THE REAL DATA (Part 1)",
                "script_line": "Otak anak tidak membangun kecerdasan dari jawaban yang benar. Otak membangun kecerdasan dari proses kebingungan: rasa mentok saat hitungan matematika nggak ketemu, coret-coret kertas berkali-kali...",
                "visual_concept": "Anak kebingungan memegang pensil menghadap kertas soal matematika penuh coretan",
                "search_query": "frustrated child doing difficult homework pencil on paper scratching head thinking hard",
                "b_roll_cue": "Cut ke pensil mencoret-coret kertas berkali-kali, simbol proses pembentukan sinapsis otak."
            },
            {
                "file_name": "04_data_child_eureka_puzzle.jpg",
                "timestamp": "[00:29 - 00:40] CONTEXT & THE REAL DATA (Part 2)",
                "script_line": "...dan kegigihan mencoba lagi sampai polanya terbuka. Di momen frustrasi itulah sinapsis saraf baru terbentuk.",
                "visual_concept": "Anak berhasil menyelesaikan teka-teki logika dengan mata berbinar penuh rasa bangga",
                "search_query": "child solving complex puzzle block problem happy focused expression achievement learning",
                "b_roll_cue": "Visual senyum kepuasan anak saat memecahkan balok/teka-teki sendiri tanpa bantuan instan."
            },
            {
                "file_name": "05_revelation_mental_resilience.jpg",
                "timestamp": "[00:40 - 00:62] THE REVELATION (THE WHY)",
                "script_line": "Saat anak dibiasakan minta jawaban ke AI setiap kali menghadapi soal sulit, kita bukan sedang melahirkan generasi jenius. Kita sedang melatih generasi yang tidak punya daya tahan mental saat dunia nyata tidak memberikan jawaban instan.",
                "visual_concept": "Anak murung menatap jendela saat hujan, menggambarkan kerapuhan mental menghadapi realitas",
                "search_query": "sad thoughtful child looking through rainy window glass feeling lonely overwhelmed",
                "b_roll_cue": "Slow zoom out anak menatap hujan. Mempertegas kekhawatiran hilangnya daya tahan mental generasi instan."
            },
            {
                "file_name": "06_ending_pondering_unsolved_puzzle.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kalau jawaban bisa dicari dalam sedetik oleh mesin, bukankah keahlian termahal anak kita nanti adalah keberanian untuk duduk tenang memikirkan teka-teki yang belum ada jawabannya? Menurut Anda gimana?",
                "visual_concept": "Anak duduk tenang membaca buku fisik di bawah naungan pohon taman",
                "search_query": "child sitting calmly outdoors under tree with open book thinking deeply looking at sky",
                "b_roll_cue": "Visual teduh anak merenung di alam terbuka. Tahan frame sebelum fade out."
            }
        ]
    },
    {
        "id": "narasi-07",
        "title": "Saat Beli Rumah, Sebenarnya Kita Sedang Membayar Siapa Tetangga Kita",
        "pillar": "PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-07",
        "scenes": [
            {
                "file_name": "01_hook_two_identical_houses.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Pernah kepikiran nggak, kenapa dua rumah dengan ukuran tanah dan kualitas semen bata yang sama persis, harganya bisa beda sampai ratusan juta rupiah?",
                "visual_concept": "Dua rumah modern berdampingan dengan bentuk dan bata yang mirip",
                "search_query": "two adjacent identical modern brick houses side by side residential neighborhood",
                "b_roll_cue": "Cut saat membongkar paradoks dua rumah yang speknya sama tapi harganya timpang."
            },
            {
                "file_name": "02_tension_exclusive_cluster_gate.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Brosur marketing biasanya nyebut ini faktor 'lokasi strategis' atau 'desain eksklusif'. Tapi kalau kita jujur pada psikologi manusia, ada satu hal tak kasat mata yang diam-diam kita bayar sangat mahal: kita sedang membayar siapa orang yang tinggal di sebelah kita.",
                "visual_concept": "Gerbang kluster perumahan mewah tertutup dengan pos keamanan modern",
                "search_query": "grand luxurious gated community security entrance gate private upscale residential cluster",
                "b_roll_cue": "Gerbang megah dengan palang otomatis, simbol batas sosial tak tertulis."
            },
            {
                "file_name": "03_data_children_playing_street.jpg",
                "timestamp": "[00:18 - 00:29] CONTEXT & THE REAL DATA (Part 1)",
                "script_line": "Sejak zaman purba, manusia selalu dihantui oleh ketakutan diasingkan dari kelompok. Di era modern, rumah bukan lagi sekadar pelindung dari hujan. Alamat rumah dan gerbang komplek telah menjadi seragam sosial tak tertulis untuk menyaring siapa kawan bermain anak kita...",
                "visual_concept": "Anak-anak komplek bermain sepeda dan berlarian di jalan komplek yang rapi",
                "search_query": "children laughing and playing together happily on quiet suburban street neighborhood",
                "b_roll_cue": "Tampilkan anak-anak bermain di jalanan kluster yang aman dan tertata rapi."
            },
            {
                "file_name": "04_data_status_signaling_suburb.jpg",
                "timestamp": "[00:29 - 00:40] CONTEXT & THE REAL DATA (Part 2)",
                "script_line": "...dan bagaimana keluarga besar menilai stabilitas hidup kita.",
                "visual_concept": "Deretan mobil dan rumah mewah modern di kawasan residensial elite",
                "search_query": "modern upscale suburban street luxury cars parked outside stylish contemporary homes",
                "b_roll_cue": "Pan halus menyusuri deretan fasad rumah mewah yang menunjukkan sinyal status sosial."
            },
            {
                "file_name": "05_revelation_status_anxiety.jpg",
                "timestamp": "[00:40 - 00:62] THE REVELATION (THE WHY)",
                "script_line": "Jadi saat orang rela mencicil miliaran rupiah di sebuah kluster tertutup, mereka sebenarnya tidak membeli batu bata. Mereka sedang membeli rasa aman dari kecemasan status mereka sendiri: ingin memastikan bahwa mereka berada di lingkungan orang-orang yang sepemikiran.",
                "visual_concept": "Seseorang menatap keluar dari balik tirai jendela rumah modern dengan raut cemas",
                "search_query": "person looking out through blinds of upscale modern home looking guarded and cautious",
                "b_roll_cue": "Pencahayaan dramatis dari balik tirai jendela rumah mewah, memvisualisasikan kecemasan status tersembunyi."
            },
            {
                "file_name": "06_ending_high_compound_walls.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Pertanyaannya: apakah dinding komplek yang tinggi itu benar-benar melindungi kedamaian keluarga kita, atau kita cuma sedang mengurung diri dari dunia nyata?",
                "visual_concept": "Tembok pembatas komplek yang tinggi membelah lingkungan di kala senja",
                "search_query": "tall concrete residential boundary wall and fence dividing neighborhood at twilight",
                "b_roll_cue": "Wide shot tembok tinggi kluster di saat senja muram, memancing penonton berpikir."
            }
        ]
    },
    {
        "id": "narasi-08",
        "title": "Ketika Rumah Pintar Tahu Semua Rahasia Kamar Tidur Kita",
        "pillar": "AI × PROPERTY × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-08",
        "scenes": [
            {
                "file_name": "01_hook_smart_speaker_camera_bedroom.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Coba perhatikan ironi ini: kita pasang gembok pintu ganda biar orang asing nggak masuk ke rumah, tapi sukarela pasang mikrofon dan kamera cloud pintar di kamar tidur kita sendiri.",
                "visual_concept": "Smart speaker / kamera pintar menyala cincin lampu biru di samping tempat tidur",
                "search_query": "smart home voice assistant speaker glowing ring next to modern bedroom bed nightstand",
                "b_roll_cue": "Close up lampu indikator smart speaker di nakas kamar tidur yang selalu mendengarkan."
            },
            {
                "file_name": "02_tension_automated_smart_lights.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Semua atas nama kenyamanan: lampu nyala otomatis pas kita masuk ruangan, AC menyesuaikan suhu tubuh, dan asisten suara memutar lagu favorit tanpa disentuh. Tapi pernah nggak kita renungkan, apa yang diam-diam hilang dari rumah kita?",
                "visual_concept": "Lampu kamar otomatis menyala lembut saat seseorang melangkah masuk",
                "search_query": "person walking into dark room lights automatically turning on ambient smart home",
                "b_roll_cue": "Transisi transisi otomatis lampu ruangan pintar menyala saat orang melangkah."
            },
            {
                "file_name": "03_data_bedroom_unmasked_vulnerability.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Secara naluri biologis, rumah adalah satu-satunya benteng terakhir di muka bumi di mana manusia bisa melepas semua topeng sosial. Tempat di mana kita bebas terlihat lelah, menangis, bertengkar dengan pasangan, atau tidur berantakan tanpa ada mata yang menilai.",
                "visual_concept": "Seseorang duduk di tepi ranjang dengan raut lelah dan rapuh tanpa topeng sosial",
                "search_query": "vulnerable person sitting on edge of bed looking tired in messy authentic bedroom safe",
                "b_roll_cue": "Shot intim dan tulus seseorang melepas lelah di atas ranjang tanpa polesan sosial."
            },
            {
                "file_name": "04_revelation_iot_sensors_surveillance.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Ketika setiap dinding dan sudut rumah dipenuhi sensor algoritma yang terus merekam data ke server komputasi, tanpa sadar tubuh kita tidak pernah benar-benar rileks...",
                "visual_concept": "Sensor IoT dan kamera pemantau berkedip merah di langit-langit apartemen",
                "search_query": "security surveillance camera red blinking led sensor mounted inside modern apartment ceiling",
                "b_roll_cue": "Sudut pandang bawah menatap sensor kamera di sudut plafon kamar."
            },
            {
                "file_name": "05_revelation_digital_glasshouse.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "...Benteng perlindungan kita telah berubah menjadi ruang pameran digital yang selalu terhubung.",
                "visual_concept": "Bayangan seseorang di dalam ruangan kaca modern yang tembus pandang dikelilingi cahaya malam",
                "search_query": "person illuminated by multiple smart screens reflections in modern glass apartment night",
                "b_roll_cue": "Pantulan cahaya digital di dinding kaca, simbol 'aquarium digital' tanpa privasi."
            },
            {
                "file_name": "06_ending_solitude_and_freedom.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kalau rumah pintar kita tahu semua rutinitas pribadi kita, di mana lagi tempat di bumi ini di mana kita bisa benar-benar sendirian dan bebas?",
                "visual_concept": "Seseorang duduk sendirian di bukit sunyi menatap langit malam bertabur bintang",
                "search_query": "lone person sitting on quiet hill mountain under starry sky truly alone with nature",
                "b_roll_cue": "Visual megah heningnya alam di bawah bintang-bintang tanpa kabel atau sinyal internet."
            }
        ]
    },
    {
        "id": "narasi-09",
        "title": "Mengapa Portofolio Gambar dan Koding Sekarang Kehilangan Nilainya?",
        "pillar": "WORK × AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-09",
        "scenes": [
            {
                "file_name": "01_hook_flawless_portfolio_screen.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Kalau Anda masih bangga pamer portofolio desain yang mulus atau baris kode yang rapi saat melamar kerja, hati-hati: cara pembuktian itu baru saja kedaluwarsa.",
                "visual_concept": "Tampilan website portofolio grafis dan baris koding yang rapi di layar laptop",
                "search_query": "slick modern digital portfolio website on laptop screen clean graphics design code",
                "b_roll_cue": "Scroll cepat portofolio desain dan koding yang sempurna di layar laptop."
            },
            {
                "file_name": "02_tension_instant_ai_generation.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Dulu, portofolio yang indah adalah tiket emas untuk meyakinkan klien atau atasan. Tapi hari ini, siapa pun yang bisa menulis prompt selama tiga puluh detik bisa menghasilkan portofolio visual yang terlihat seperti karya profesional berpengalaman sepuluh tahun.",
                "visual_concept": "Tangan mengetik prompt di keyboard dengan visual ilustrasi digital seketika bermunculan",
                "search_query": "person typing on glowing mechanical keyboard producing instant digital artwork prompts",
                "b_roll_cue": "Fast typing on mechanical keyboard dan artwork digital langsung tercipta otomatis."
            },
            {
                "file_name": "03_data_market_value_crash.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Ketika hasil akhir karya (the output) bisa dibuat dalam sekejap tanpa biaya oleh kecerdasan buatan, nilai pasar dari output itu otomatis anjlok mendekati nol. Klien dan perusahaan sekarang tidak lagi terkesan dengan seberapa bagus hasil jadinya.",
                "visual_concept": "Klien bisnis tampak bosan dan tidak terkesan melihat presentasi desain di layar laptop",
                "search_query": "confused business client looking unimpressed at design presentation on laptop screen",
                "b_roll_cue": "Ekspresi bos/klien yang flat dan tidak lagi kagum pada portofolio visual standar."
            },
            {
                "file_name": "04_revelation_trust_and_crisis.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Mata uang baru di dunia kerja bukan lagi 'apa yang bisa Anda tunjukkan', melainkan 'seberapa bisa Anda dipercaya untuk bertanggung jawab saat sistem bermasalah'...",
                "visual_concept": "Insinyur profesional tenang dan tegas mengatasi krisis teknis di ruang kontrol",
                "search_query": "reliable engineer professional handling urgent technical server crisis calm confident leader",
                "b_roll_cue": "Visual ketenangan profesional menghadapi masalah tak terduga, nilai nyata manusia."
            },
            {
                "file_name": "05_revelation_human_handshake.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "...Keberanian mengambil keputusan dan integritas rekam jejak personal adalah hal yang tidak bisa diprompt oleh bot.",
                "visual_concept": "Jabat tangan erat dua mitra bisnis dengan tatapan mata saling percaya dan berintegritas",
                "search_query": "firm professional business handshake two people eye contact trust integrity deal",
                "b_roll_cue": "Close up jabat tangan erat dan kontak mata, simbol kontrak kepercayaan dan integritas."
            },
            {
                "file_name": "06_ending_unique_human_worth.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Pertanyaannya: kalau hasil karya teknis Anda bisa ditiru AI dalam lima detik, apa satu alasan klien harus tetap memilih Anda sebagai manusianya?",
                "visual_concept": "Potret wajah pembuat karya / desainer menatap tajam ke lensa kamera penuh keyakinan",
                "search_query": "confident thoughtful artisan craftsperson looking directly into camera authentic human eye",
                "b_roll_cue": "Tatapan langsung ke lensa kamera dengan raut wajah berkarakter. Tahan hingga penutupan."
            }
        ]
    },
    {
        "id": "narasi-10",
        "title": "Alasan Sebenarnya Kenapa Pekerja Muda Mulai Kabur dari Jakarta",
        "pillar": "PROPERTY × FUTURE × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-10",
        "scenes": [
            {
                "file_name": "01_hook_moving_boxes_farewell.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Pernah perhatiin nggak, kenapa belakangan ini makin banyak teman kantor kita yang tiba-tiba pamit pindah tinggal ke luar kota atau pinggiran bukit?",
                "visual_concept": "Pekerja muda merapikan tumpukan kardus pindahan rumah di apartemen kota",
                "search_query": "young person packing cardboard moving boxes in city apartment leaving town moving out",
                "b_roll_cue": "Tumpukan kardus bertuliskan 'moving' dan tas ransel siap berangkat meninggalkan kota."
            },
            {
                "file_name": "02_tension_jakarta_traffic_commute.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Secara hitungan lama, Jakarta dan kota megapolitan adalah pusat uang, pusat pergaulan, dan pusat karier tertinggi. Tapi anehnya, orang-orang dengan penghasilan stabil justru memilih meninggalkan gemerlap kota besar dan beli tanah di tempat yang jauh lebih tenang.",
                "visual_concept": "Kemacetan parah kota megapolitan dengan asap knalpot dan lautan lampu mobil merah di senja hari",
                "search_query": "exhausting heavy metropolitan city traffic jam exhaust smoke crowded road dusk",
                "b_roll_cue": "Lautan lampu rem mobil merah dalam kemacetan panjang tanpa ujung di bawah flyover."
            },
            {
                "file_name": "03_data_remote_work_cloud.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Kenapa bisa begitu? Karena revolusi industri dulu memaksa manusia berkerumun dekat pabrik dan gedung kantor demi mencari nafkah. Tapi hari ini, ketika laptop dan sistem cloud memungkinkan kita bekerja dari mana saja, otak manusia mulai menuntut hak biologisnya kembali.",
                "visual_concept": "Seseorang bekerja di laptop dari teras rumah dengan latar lembah pegunungan berkabut",
                "search_query": "person working on laptop with cup of coffee overlooking misty mountain valley terrace",
                "b_roll_cue": "Pemandangan laptop di atas meja kayu dengan latar belakang hijau pegunungan yang asri."
            },
            {
                "file_name": "04_revelation_concrete_prison_box.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Manusia tidak pernah berevolusi untuk hidup di dalam kotak beton sempit, menghirup asap knalpot dua jam sehari, dan mendengar klakson macet...",
                "visual_concept": "Deretan gedung apartemen beton tinggi yang padat dan terasa mengurung",
                "search_query": "claustrophobic dense concrete apartment blocks brutalist urban density high rise",
                "b_roll_cue": "Gedung-gedung beton tinggi rapat yang monoton dan menjulang dingin."
            },
            {
                "file_name": "05_revelation_fresh_air_garden.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "...Begitu kerja jarak jauh membebaskan lokasi kita, orang-orang cerdas langsung menukar kemacetan dengan udara bersih dan pekarangan tanah nyata.",
                "visual_concept": "Anak muda menyiram tanaman di pekarangan tanah hijau dengan senyum lepas di pagi hari",
                "search_query": "young person tending green backyard garden barefoot fresh morning air smiling",
                "b_roll_cue": "Kaki telanjang menginjak rumput hijau dan tanah basah, simbol kembali ke fitrah manusia."
            },
            {
                "file_name": "06_ending_escape_the_hustle.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kalau pekerjaan Anda besok pagi bisa dikerjakan seratus persen dari mana saja, apakah Anda masih mau bertahan di tengah hiruk-pikuk macetnya kota besar?",
                "visual_concept": "Seseorang berdiri di puncak bukit menatap cakrawala pegunungan yang luas dan sejuk",
                "search_query": "backpacker traveler standing on quiet hilltop looking at distant misty mountain horizon",
                "b_roll_cue": "Punggung seseorang menatap kebebasan alam terbuka tanpa batas di perbukitan."
            }
        ]
    },
    {
        "id": "narasi-11",
        "title": "Dikelilingi 8 Miliar Manusia, tapi Curhatnya ke Bot AI",
        "pillar": "AI × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-11",
        "scenes": [
            {
                "file_name": "01_hook_typing_confession_chatbot.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Ada satu fenomena yang kedengarannya sepele tapi bikin bulu kuduk berdiri: semakin hari, semakin banyak orang yang memilih curhat ke chatbot AI dibanding ke pasangannya sendiri.",
                "visual_concept": "Jari mengetik pesan curhat yang panjang di aplikasi chat AI malam hari",
                "search_query": "close up hand typing emotional personal text message into chatbot app on phone at night",
                "b_roll_cue": "Extreme close up jemari mengetik curahan hati di aplikasi chat pada larut malam."
            },
            {
                "file_name": "02_tension_crowded_city_isolation.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Kita hidup di planet dengan delapan miliar manusia dan ribuan kontak di media sosial. Tapi anehnya, saat hati kita hancur atau pikiran lagi kalut, kita justru merasa paling aman mengetik curahan hati ke kotak teks algoritma di layar smartphone.",
                "visual_concept": "Satu orang berdiri diam di tengah lautan orang yang bergerak kabur di stasiun kota",
                "search_query": "solitary lonely person standing in blurred crowd of moving city commuters feeling isolated",
                "b_roll_cue": "Motion blur orang-orang berlalu-lalang sementara subjek berdiri membisu di tengah."
            },
            {
                "file_name": "03_data_judgment_free_listener.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Kenapa kita melakukan itu? Jawabannya bukan karena AI itu pintar. Jawabannya karena manusia di sekitar kita seringkali terlalu sibuk, gampang menghakimi, atau memotong omongan kita dengan nasihat sok tahu. AI memberikan apa yang langka di dunia nyata: pendengar setia yang tidak pernah capek dan tidak pernah menilai kita salah.",
                "visual_concept": "Seseorang mendekap smartphone di dada dengan perasaan lega merasa didengarkan",
                "search_query": "sad person holding smartphone to chest tears or relief feeling heard by screen glowing",
                "b_roll_cue": "Pencahayaan redup, pelukan tangan memegang ponsel di dada dalam keheningan kamar."
            },
            {
                "file_name": "04_revelation_synthetic_empathy_mirror.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Tapi inilah bahayanya empati sintetis. AI memang bisa menenangkan kita di malam hari, tapi ia tidak punya detak jantung, tidak bisa memeluk, dan tidak pernah benar-benar peduli...",
                "visual_concept": "Wajah seseorang menatap bayangan cermin retak yang dingin tanpa jiwa",
                "search_query": "person looking into broken mirror reflection distorted sorrowful digital solitude",
                "b_roll_cue": "Visual cermin retak mempertegas bahwa AI hanyalah refleksi diri tanpa jiwa."
            },
            {
                "file_name": "05_revelation_cold_metal_screen.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "...Kita sedang mengobati kesepian manusia dengan cermin mekanik yang hanya memantulkan suara kita sendiri.",
                "visual_concept": "Siluet seseorang duduk meringkuk di sudut ruangan gelap hanya disinari cahaya ponsel dingin",
                "search_query": "silhouette of lonely person sitting against wall in dark room illuminated by cold smartphone",
                "b_roll_cue": "Siluet kesendirian di sudut ruangan gelap dengan pantulan cahaya kotak ponsel."
            },
            {
                "file_name": "06_ending_face_to_face_eye_contact.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kapan terakhir kali Anda duduk berdua dengan seseorang, menatap matanya, dan mendengar ceritanya tanpa ada HP di atas meja?",
                "visual_concept": "Dua orang sahabat duduk berhadapan saling menatap mata dan tertawa hangat di kafe",
                "search_query": "two close friends or couple sitting together in coffee shop looking into each other eyes smiling genuine",
                "b_roll_cue": "Visual kontak mata hangat dan tulus dua manusia tanpa gadget di meja. Fade to black."
            }
        ]
    },
    {
        "id": "narasi-12",
        "title": "Mengapa Rumah Orang Tua Seringkali Berubah Jadi Sunyi dan Sengketa?",
        "pillar": "PROPERTY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-12",
        "scenes": [
            {
                "file_name": "01_hook_padlocked_old_family_house.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Pernah nggak lewat di depan rumah tua keluarga yang dulu pas lebaran ramai banget oleh tawa anak-cucu, tapi sekarang pintunya digembok dan halamannya dipenuhi rumput liar?",
                "visual_concept": "Pintu pagar rumah tua keluarga yang digembok rapat dengan halaman dipenuhi ilalang",
                "search_query": "old vintage family house with closed padlocked gate overgrown weeds quiet overgrown yard",
                "b_roll_cue": "Gembok berkarat di pintu pagar tua dengan ilalang liar di pekarangan tak terawat."
            },
            {
                "file_name": "02_tension_nostalgic_family_laughter.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Orang tua kita dulu berjuang puluhan tahun, menahan lapar dan banting tulang, cuma demi satu mimpi: membangun rumah besar agar seluruh keluarga bisa berkumpul selamanya...",
                "visual_concept": "Kenangan nostalgia keluarga besar berkumpul di meja makan penuh tawa dan kehangatan",
                "search_query": "warm vintage memory of happy multigenerational family gathering around dining table laughing",
                "b_roll_cue": "Warm vintage filter: tawa keluarga besar tiga generasi makan bersama di masa lalu."
            },
            {
                "file_name": "03_data_for_sale_sign_dispute.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "...Tapi begitu orang tua tiada, rumah megah itu kerap jadi rebutan waris atau dijual murah karena nggak ada anak yang mau menempatinya.",
                "visual_concept": "Spanduk 'Rumah Ini Dijual' terpasang miring di dinding rumah tua yang sepi berdebu",
                "search_query": "for sale real estate banner on old abandoned grand family house empty dusty windows",
                "b_roll_cue": "Spanduk 'Dijual' yang mulai lusuh di dinding rumah peninggalan keluarga."
            },
            {
                "file_name": "04_data_cold_concrete_walls.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Kenapa realitas ini berulang di begitu banyak keluarga? Karena kita sering salah paham mengira bahwa yang membuat keluarga bersatu adalah sertifikat tanah dan dinding batanya...",
                "visual_concept": "Ruang tamu rumah tua yang kosong melompong dengan debu beterbangan di berkas sinar matahari",
                "search_query": "cold empty interior of old house dust particles in light sunbeam bare concrete floors",
                "b_roll_cue": "Partikel debu melayang di ruang tamu kosong yang dingin tanpa perabot."
            },
            {
                "file_name": "05_revelation_welcoming_grandparent.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "Rumah fisik hanyalah wadah kosong. Jiwa pemersatunya bukan pada bangunannya, melainkan pada sosok yang menyambut di depan pintu. Begitu sosok pemaaf itu tiada, rumah megah sekalipun langsung menyusut kembali menjadi tumpukan semen beku yang kehilangan maknanya.",
                "visual_concept": "Sosok nenek/kakek tersenyum ramah dan penuh kasih menyambut di ambang pintu rumah",
                "search_query": "warm loving elderly grandmother grandfather smiling welcoming with open arms at front door",
                "b_roll_cue": "Wajah penuh cinta kakek/nenek tersenyum di pintu, sosok sejati 'jiwa sebuah rumah'."
            },
            {
                "file_name": "06_ending_kissing_parents_hand.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Bagi Anda yang orang tuanya masih ada hari ini: kapan terakhir kali Anda pulang ke rumah bukan untuk urusan uang, tapi cuma untuk mencium tangannya?",
                "visual_concept": "Anak memegang dan mencium tangan orang tua yang sudah berkerut dengan penuh rasa hormat dan kasih",
                "search_query": "adult child holding and kissing elderly parent aged wrinkled hands with deep love respect",
                "b_roll_cue": "Close up tangan anak mencium punggung tangan tua orang tuanya dengan haru."
            }
        ]
    },
    {
        "id": "narasi-13",
        "title": "Mengapa Makin Banyak Scrolling Video Pendek, Jiwa Kita Makin Kosong?",
        "pillar": "TECHNOLOGY × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-13",
        "scenes": [
            {
                "file_name": "01_hook_lying_in_bed_scrolling.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Pernah nggak, rebahan niatnya cuma mau refreshing lima menit scrolling video, tapi pas bangun satu jam kemudian badan malah rasanya makin pegal dan otak makin hampa?",
                "visual_concept": "Seseorang rebahan di kasur gelap memegang HP scrolling dengan tatapan mata mati rasa",
                "search_query": "person lying in messy bed dark room holding smartphone scrolling tired eyes numbness",
                "b_roll_cue": "Shot dari atas kasur seseorang rebahan menatap layar HP dengan mata sayu."
            },
            {
                "file_name": "02_tension_endless_entertaining_stream.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Secara teori, kita sedang menonton konten hiburan yang lucu, informatif, dan seru. Tapi kenapa setelah ratusan video lewat di layar, perasaan yang tertinggal di dalam dada bukan rasa puas, melainkan rasa gelisah yang aneh?",
                "visual_concept": "Kilatan warna-warni video pendek terpantul di wajah seseorang yang tampak hampa tanpa ekspresi",
                "search_query": "colorful vibrant video clips light reflections on tired person blank expressionless face",
                "b_roll_cue": "Lampu layar warna-warni berganti tiap detik memantul pada wajah yang tanpa senyum."
            },
            {
                "file_name": "03_data_dopamine_crash_cycle.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Otak biologis manusia berevolusi untuk memproses cerita yang utuh: ada awal, ada perjuangan di tengah, dan ada penyelesaian di akhir. Tapi algoritma video pendek menyuntikkan klimaks instan setiap sepuluh detik tanpa memberi jeda bagi otak untuk mencerna makna.",
                "visual_concept": "Ilustrasi neuron saraf otak yang kelelahan akibat stimulasi dopamin berlebihan",
                "search_query": "abstract representation of brain neurons exhausted dopamine overload synaptic exhaustion",
                "b_roll_cue": "Visualisasi neuron otak atau jaringan saraf yang over-stimulasi."
            },
            {
                "file_name": "04_revelation_fragmented_emotions.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "Akibatnya, reseptor dopamin kita mengalami kebas karena over-stimulasi. Otak kita kelelahan bukan karena berpikir keras, melainkan karena dibombardir serpihan emosi yang putus-putus...",
                "visual_concept": "Seseorang duduk di lantai bersandar dinding menatap kosong ke udara dengan rasa lelah emosional",
                "search_query": "exhausted person sitting on floor head against wall staring into blank space depleted",
                "b_roll_cue": "Duduk bersandar di dinding dengan pandangan kosong, visual kelelahan dopamin."
            },
            {
                "file_name": "05_revelation_phone_face_down.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "...tanpa pernah terhubung menjadi pemahaman yang utuh.",
                "visual_concept": "Tangan meletakkan smartphone dengan layar tertelungkup ke bawah di atas meja kayu",
                "search_query": "person placing smartphone face down on table taking deep exhale letting go",
                "b_roll_cue": "Smartphone diletakkan menghadap ke bawah di meja kayu, simbol jeda kognitif."
            },
            {
                "file_name": "06_ending_resting_eyes_real_world.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kapan terakhir kali Anda mematikan layar, menaruh HP di ruangan lain, dan membiarkan mata Anda menikmati pemandangan nyata di sekitar Anda?",
                "visual_concept": "Seseorang duduk santai di balkon menatap langit senja nyata tanpa gawai di tangan",
                "search_query": "person sitting quietly on balcony enjoying sunset horizon with no devices present peaceful",
                "b_roll_cue": "Pandangan mata lepas ke langit senja asli tanpa ada layar gadget."
            }
        ]
    },
    {
        "id": "narasi-14",
        "title": "Akhir dari Era Gedung Kantor Pencakar Langit",
        "pillar": "AI × PROPERTY × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-14",
        "scenes": [
            {
                "file_name": "01_hook_glowing_skyscraper_empty_floors.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Pernah perhatiin gedung-gedung kaca pencakar langit di kawasan bisnis pusat kota? Megah, berkilau di malam hari, tapi di jam kerja ruangannya banyak yang sepi melompong.",
                "visual_concept": "Gedung pencakar langit kaca megah di kawasan CBD menjulang ke langit kota",
                "search_query": "majestic glass skyscraper tower looking up commercial central business district modern architecture",
                "b_roll_cue": "Low angle menatap ke atas gedung pencakar langit kaca megah yang menjulang."
            },
            {
                "file_name": "02_tension_empty_office_cubicles.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Perusahaan multinasional rela membayar sewa miliaran rupiah per lantai tiap tahunnya. Tapi anehnya, survei kehadiran karyawan menunjukkan rata-rata meja kantor modern cuma terisi empat puluh persen dari kapasitasnya.",
                "visual_concept": "Lantai kantor korporat modern dengan deretan kubikel dan kursi kosong tanpa orang",
                "search_query": "empty modern office floor vacant desk cubicles chairs quiet daylight corporate interior",
                "b_roll_cue": "Pan vertikal menyusuri meja-meja kantor yang kosong melompong di siang hari."
            },
            {
                "file_name": "03_data_industrial_admin_factory.jpg",
                "timestamp": "[00:18 - 00:29] CONTEXT & THE REAL DATA (Part 1)",
                "script_line": "Kenapa bisa begitu? Karena konsep gedung kantor bertingkat diciptakan pada abad ke-20 sebagai pabrik administrasi: atasan butuh melihat bawahan duduk rapi di kubikel biar yakin mereka bekerja...",
                "visual_concept": "Foto vintage pegawai kantor abad 20 duduk berjejer rapi di mesin ketik seperti pabrik",
                "search_query": "vintage black and white typing pool office workers in rows cubicles 20th century factory style",
                "b_roll_cue": "Vintage grayscale visual: deretan meja pegawai abad 20 yang berbaris mekanis."
            },
            {
                "file_name": "04_data_ai_agents_automation.jpg",
                "timestamp": "[00:29 - 00:40] CONTEXT & THE REAL DATA (Part 2)",
                "script_line": "...Tapi di era sekarang, ketika agen AI dan software kolaborasi menangani tugas teknis secara otomatis, kehadiran fisik di meja kantor kehilangan maknanya.",
                "visual_concept": "Layar software agen AI otomasi alur kerja modern berpendar di layar tipis",
                "search_query": "modern software automated data analytics dashboard interface glowing blue on sleek screen",
                "b_roll_cue": "Cut ke dashboard AI agent yang memproses ribuan data otomatis tanpa butuh orang duduk."
            },
            {
                "file_name": "05_revelation_collaboration_creative_hub.jpg",
                "timestamp": "[00:40 - 00:62] THE REVELATION (THE WHY)",
                "script_line": "Memaksa manusia terjebak macet dua jam di jalanan cuma buat duduk membuka laptop di gedung bertingkat adalah pemborosan energi peradaban yang konyol. Gedung kantor di masa depan bukan lagi tempat mengerjakan tugas rutin, melainkan tempat berkumpul untuk diskusi ide besar yang butuh tatap muka.",
                "visual_concept": "Tim kreatif berdiri di depan papan tulis mendiskusikan gagasan besar bersama sambil tersenyum",
                "search_query": "collaborative modern creative team standing around whiteboard sketching big ideas together smiling",
                "b_roll_cue": "Ruang kolaboratif hangat: orang berdiri berdiskusi di depan papan gagasan besar."
            },
            {
                "file_name": "06_ending_future_workspace_city.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Kalau tugas Anda bisa dikerjakan di mana saja dengan bantuan AI, menurut Anda apa fungsi utama dari sebuah kantor fisik sepuluh tahun ke depan?",
                "visual_concept": "Seseorang berdiri di teras atap gedung menatap cakrawala kota saat senja memikirkan masa depan",
                "search_query": "thoughtful architect standing on rooftop terrace overlooking modern city skyline contemplating",
                "b_roll_cue": "Sosok menatap lanskap gedung-gedung kota dari teras atap di kala senja."
            }
        ]
    },
    {
        "id": "narasi-15",
        "title": "Di Era AI Bisa Segalanya, Apa yang Membuat Manusia Tetap Bernilai?",
        "pillar": "FUTURE × HUMAN × WHY",
        "folder": r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\narasi-15",
        "scenes": [
            {
                "file_name": "01_hook_ai_generating_everything.jpg",
                "timestamp": "[00:00 - 00:05] HOOK",
                "script_line": "Ketika AI sekarang bisa nulis esai dalam sedetik, bikin program rumit, sampai mendiagnosis penyakit lebih cepat dari dokter biasa—pernah nggak Anda bertanya: lalu apa gunanya kita sebagai manusia?",
                "visual_concept": "Visualisasi otak digital AI dengan aliran data saraf kecerdasan buatan",
                "search_query": "futuristic artificial intelligence neural network data stream holographic brain medical code",
                "b_roll_cue": "Visual futuristik jaringan saraf kecerdasan buatan dan kode data komputasi."
            },
            {
                "file_name": "02_tension_existential_fear_worker.jpg",
                "timestamp": "[00:05 - 00:18] TENSION & PARADOX",
                "script_line": "Pertanyaan ini bikin jutaan orang cemas dan gamang. Selama ratusan tahun, kita diajarkan bahwa nilai harga diri seseorang ditentukan oleh keahlian teknis yang ia miliki: seberapa jago berhitung, seberapa pintar menghafal, atau seberapa cepat menganalisis data.",
                "visual_concept": "Seseorang duduk merenung cemas di kantor gelap memikirkan masa depan karirnya",
                "search_query": "worried professional sitting in dark office contemplating future existential anxiety",
                "b_roll_cue": "Raut wajah cemas pekerja profesional menatap kegelapan ruang kerja."
            },
            {
                "file_name": "03_data_human_liberation.jpg",
                "timestamp": "[00:18 - 00:40] CONTEXT & THE REAL DATA",
                "script_line": "Tapi ketika mesin terbukti bisa melakukan semua kemampuan kalkulasi itu jauh lebih sempurna dibanding otak kita, banyak orang merasa eksistensi dirinya mendadak terancam. Padahal kalau kita renungkan lebih dalam, krisis ini justru adalah kabar baik bagi peradaban.",
                "visual_concept": "Sinar matahari fajar keemasan memecah awan mendung, simbol harapan dan pembebasan era baru",
                "search_query": "warm golden sunrise breaking through dark clouds symbol of hope new era",
                "b_roll_cue": "Fajar keemasan menyinari bumi menembus awan gelap, simbol transformasi peradaban."
            },
            {
                "file_name": "04_revelation_empathy_compassion.jpg",
                "timestamp": "[00:40 - 00:51] THE REVELATION (THE WHY - Part 1)",
                "script_line": "AI membebaskan kita dari ilusi bahwa manusia adalah mesin kalkulator biologis. Nilai tertinggi manusia tidak pernah terletak pada seberapa cepat kita mengolah data. Nilai sejati manusia terletak pada keberanian mengambil tanggung jawab moral, kemampuan berempati menatap penderitaan sesama...",
                "visual_concept": "Tangan seseorang menggenggam tangan orang lain dengan penuh kasih dan empati saling menguatkan",
                "search_query": "compassionate caring person holding hands supporting comfort empathy helping other human",
                "b_roll_cue": "Close up tangan saling menggenggam tulus, menonjolkan empati dan sentuhan biologis."
            },
            {
                "file_name": "05_revelation_unconditional_human_love.jpg",
                "timestamp": "[00:51 - 00:62] THE REVELATION (THE WHY - Part 2)",
                "script_line": "...dan cinta kasih tulus yang menolak digantikan oleh baris kode apa pun.",
                "visual_concept": "Pelukan hangat tulus dua insan manusia yang saling menyayangi dengan sepenuh hati",
                "search_query": "genuine warm embrace hug between two people true human love and connection",
                "b_roll_cue": "Pelukan tulus dua insan, ekspresi cinta murni yang tidak bisa diprogram oleh AI."
            },
            {
                "file_name": "06_ending_core_human_spark.jpg",
                "timestamp": "[00:62 - 00:75] OPEN QUESTION (PENUTUP REFLEKTIF)",
                "script_line": "Di dunia yang semakin serba otomatis dan cerdas, satu sifat kemanusiaan apa di dalam diri Anda yang paling Anda jaga agar tidak pernah pudar?",
                "visual_concept": "Close up mata manusia yang jernih dan ekspresif memancarkan cahaya jiwa dan kedalaman batin",
                "search_query": "close up expressive human eye iris reflection of light soul depth authentic portrait",
                "b_roll_cue": "Extreme close up bola mata manusia dengan kilau cahaya jiwa. Fade out perlahan."
            }
        ]
    }
]

def main():
    session_id = init_mcp_session()
    
    # Load existing manifest if present
    manifest_path = r"c:\Users\Nugi\Documents\nugi-konten-kreator\output\OVERALL_ASSETS_MANIFEST.json"
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                overall_manifest = json.load(f)
        except Exception:
            overall_manifest = {}
    else:
        overall_manifest = {}

    for plan in NARASI_PLANS_PART2:
        narasi_id = plan["id"]
        narasi_title = plan["title"]
        assets_dir = os.path.join(plan["folder"], "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        print(f"\n=======================================================")
        print(f"Processing {narasi_id}: {narasi_title}")
        print(f"Target folder: {assets_dir}")
        print(f"=======================================================")
        
        downloaded_assets = []
        
        for idx, scene in enumerate(plan["scenes"]):
            file_name = scene["file_name"]
            target_path = os.path.join(assets_dir, file_name)
            query = scene["search_query"]
            print(f"\n[{idx+1}/{len(plan['scenes'])}] Searching for: '{query}'...")
            
            try:
                results = search_photos(session_id, query, orientation="portrait")
                if not results:
                    print(f"  Warning: No portrait results for query, trying fallback broader search...")
                    results = search_photos(session_id, query[:60], orientation="portrait")
                
                if results:
                    chosen = results[0]
                    urls = chosen.get("urls", {})
                    img_url = urls.get("large") or urls.get("regular") or urls.get("full") or chosen.get("image_url")
                    
                    print(f"  Downloading from: {img_url}")
                    size_bytes = download_image(img_url, target_path)
                    print(f"  Saved {file_name} ({size_bytes:,} bytes)")
                    
                    asset_info = {
                        "file_name": file_name,
                        "timestamp": scene["timestamp"],
                        "script_line": scene["script_line"],
                        "visual_concept": scene["visual_concept"],
                        "b_roll_cue": scene["b_roll_cue"],
                        "photo_id": chosen.get("photo_id"),
                        "photographer": chosen.get("photographer_username") or chosen.get("photographer") or "Pexels Creator",
                        "source": chosen.get("source", "Pexels"),
                        "license": chosen.get("license_type", "Free to use"),
                        "source_url": chosen.get("source_image_url") or chosen.get("image_url"),
                        "description": chosen.get("description") or chosen.get("source_description", ""),
                        "dimensions": f"{chosen.get('width', '-')} x {chosen.get('height', '-')}",
                        "orientation": chosen.get("orientation", "portrait")
                    }
                    downloaded_assets.append(asset_info)
                else:
                    print(f"  ERROR: No image found for scene {file_name}")
            except Exception as e:
                print(f"  Error processing scene {file_name}: {e}")
            
            time.sleep(0.4)
            
        # Write ASSETS_INDEX.md in assets/ folder
        index_md_path = os.path.join(assets_dir, "ASSETS_INDEX.md")
        with open(index_md_path, "w", encoding="utf-8") as f:
            f.write(f"# 📸 Index Aset Visual: {narasi_title}\n\n")
            f.write(f"- **Pilar DNA:** `{plan['pillar']}`\n")
            f.write(f"- **Format:** Vertical 9:16 (TikTok / Instagram Reels / YouTube Shorts)\n")
            f.write(f"- **Penyedia Aset:** Pexafy MCP (Pexels / Pixabay / Unsplash License Free)\n\n")
            f.write(f"---\n\n")
            f.write(f"## 📋 Daftar Aset & Petunjuk Editing (B-Roll Cue Sheet)\n\n")
            
            for item in downloaded_assets:
                f.write(f"### 🖼️ `{item['file_name']}`\n")
                f.write(f"- **Timeline Naskah:** `{item['timestamp']}`\n")
                f.write(f"- **Kutipan Naskah:** *\"{item['script_line']}\"*\n")
                f.write(f"- **Konsep Visual:** {item['visual_concept']}\n")
                f.write(f"- **🎬 Instruksi Editor (B-Roll):** {item['b_roll_cue']}\n")
                f.write(f"- **Fotografer / Author:** {item['photographer']} ({item['source']})\n")
                f.write(f"- **Resolusi Asli:** {item['dimensions']} | Orientasi: {item['orientation']}\n")
                f.write(f"- **Deskripsi Gambar:** {item['description']}\n")
                f.write(f"- **Sumber URL:** [{item['source']}]({item['source_url']})\n\n")
                f.write(f"---\n\n")
                
        print(f"Generated index: {index_md_path}")
        
        # Write SCRIPT_AND_STORYBOARD.md in root of narasi folder
        storyboard_path = os.path.join(plan["folder"], "SCRIPT_AND_STORYBOARD.md")
        with open(storyboard_path, "w", encoding="utf-8") as f:
            f.write(f"# 🎬 Storyboard & Naskah Produksi: {narasi_title}\n\n")
            f.write(f"**Pilar Konten:** `{plan['pillar']}`  \n")
            f.write(f"**Karakter Suara:** Conversational, jujur, tenang, reflektif, tanpa jargon klise AI.  \n")
            f.write(f"**Rasio Video:** 9:16 Vertical Video (TikTok / Shorts / Reels)  \n\n")
            f.write(f"---\n\n")
            f.write(f"## 🎞️ Storyboard Sekuensial (Talking Head + B-Roll Overlay)\n\n")
            f.write(f"| Timestamp | Tipe Visual | Aset B-Roll | Panduan Kamera / Editor |\n")
            f.write(f"| :--- | :--- | :--- | :--- |\n")
            for item in downloaded_assets:
                f.write(f"| `{item['timestamp']}` | Talking Head + B-Roll Cut | `assets/{item['file_name']}` | {item['b_roll_cue']} |\n")
            f.write(f"\n---\n\n")
            f.write(f"## 📜 Naskah Lengkap & Cue Aset\n\n")
            for item in downloaded_assets:
                f.write(f"#### {item['timestamp']}\n")
                f.write(f"> **NUGI (Talking Head):**\n")
                f.write(f"> \"{item['script_line']}\"\n\n")
                f.write(f"*(🎬 **B-ROLL CUE:** Tampilkan `assets/{item['file_name']}` - {item['visual_concept']} - {item['b_roll_cue']})*\n\n")
                
        print(f"Generated storyboard: {storyboard_path}")
        overall_manifest[narasi_id] = downloaded_assets

    # Save overall manifest
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(overall_manifest, f, indent=2)
    print(f"\nCompleted! All 10 narasi (part 2) processed and saved to {manifest_path}")

if __name__ == "__main__":
    main()
