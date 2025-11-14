from pymongo import MongoClient
from datetime import datetime

# ====== KONFIGURASI MONGODB ======
client = MongoClient("mongodb://127.0.0.1:27017")
db = client["toko_jus"]
users_col = db["users"]
orders_col = db["orders"]

SALDO_AWAL = 100000

# ====== DATA MENU JUS ======
JUS_MENU = {
    1: {"nama": "Jus Jeruk", "harga": 8000},
    2: {"nama": "Jus Mangga", "harga": 10000},
    3: {"nama": "Jus Alpukat", "harga": 12000},
    4: {"nama": "Jus Jambu", "harga": 9000},
    5: {"nama": "Jus Melon", "harga": 8500},
}

current_user = None  # Menyimpan user yang sedang login


# ====== FUNGSI UTILITAS ======
def format_rupiah(angka: int) -> str:
    return f"Rp{angka:,}".replace(",", ".")


def format_tanggal(dt: datetime) -> str:
    return dt.strftime("%d-%m-%Y %H:%M:%S")


# ====== AUTENTIKASI USER ======
def registrasi():
    print("\n" + "=" * 40)
    print("            REGISTRASI")
    print("=" * 40)

    username = input("Masukkan username: ").strip()
    if not username:
        print("Username tidak boleh kosong!\n")
        return

    # Cek apakah username sudah terdaftar
    existing = users_col.find_one({"username": username})
    if existing:
        print("❌ Username sudah digunakan. Coba yang lain.\n")
        return

    password = input("Masukkan password: ").strip()
    if not password:
        print("Password tidak boleh kosong!\n")
        return

    # Simpan ke database
    user_doc = {
        "username": username,
        "password": password,  # NOTE: untuk real app sebaiknya di-hash
        "saldo": SALDO_AWAL,
        "created_at": datetime.now(),
    }
    users_col.insert_one(user_doc)

    print(f"\n✔ Registrasi berhasil untuk user '{username}'")
    print(f"Saldo awal: {format_rupiah(SALDO_AWAL)}\n")


def login():
    global current_user

    if current_user is not None:
        print(f"\nAnda sudah login sebagai: {current_user['username']}")
        return

    print("\n" + "=" * 40)
    print("              LOGIN")
    print("=" * 40)

    username = input("Username: ").strip()
    password = input("Password: ").strip()

    user = users_col.find_one({"username": username})

    if not user or user["password"] != password:
        print("❌ Username atau password salah.\n")
        return

    current_user = user
    print(f"\n✔ Login berhasil. Selamat datang, {current_user['username']}!")
    print(f"Saldo Anda: {format_rupiah(current_user['saldo'])}\n")


def logout():
    global current_user
    if current_user is None:
        print("\nAnda belum login.\n")
        return
    print(f"\n✔ User '{current_user['username']}' telah logout.\n")
    current_user = None


# ====== MENU JUS & PEMESANAN ======
def tampilkan_menu_jus():
    print("=" * 40)
    print("             MENU JUS")
    print("=" * 40)
    for kode, item in JUS_MENU.items():
        print(f"{kode}. {item['nama']} - {format_rupiah(item['harga'])}")
    print("0. Selesai & Bayar")
    print("=" * 40)


def pesan_jus():
    global current_user

    if current_user is None:
        print("\n❌ Harus login dulu sebelum memesan jus!\n")
        return

    # Refresh data user dari database (biar saldo terupdate)
    current_user = users_col.find_one({"_id": current_user["_id"]})

    pesanan = []
    total = 0

    while True:
        tampilkan_menu_jus()

        try:
            pilihan = int(input("Pilih menu (0 untuk selesai): "))
        except ValueError:
            print("Input harus angka!\n")
            continue

        if pilihan == 0:
            break

        if pilihan not in JUS_MENU:
            print("Menu tidak tersedia!\n")
            continue

        try:
            jumlah = int(input("Masukkan jumlah: "))
        except ValueError:
            print("Jumlah harus angka!\n")
            continue

        if jumlah <= 0:
            print("Jumlah harus lebih dari 0!\n")
            continue

        nama = JUS_MENU[pilihan]["nama"]
        harga = JUS_MENU[pilihan]["harga"]
        subtotal = harga * jumlah

        pesanan.append({
            "nama": nama,
            "harga": harga,
            "jumlah": jumlah,
            "subtotal": subtotal
        })

        total += subtotal
        print(f"Ditambahkan {jumlah}x {nama} (subtotal: {format_rupiah(subtotal)})")
        print(f"Total sementara: {format_rupiah(total)}\n")

    if not pesanan:
        print("\nAnda tidak memesan apa pun.\n")
        return

    print("\n" + "=" * 40)
    print("          STRUK PEMESANAN")
    print("=" * 40)
    for i, item in enumerate(pesanan, start=1):
        print(f"{i}. {item['nama']} x{item['jumlah']} = {format_rupiah(item['subtotal'])}")
    print("-" * 40)
    print(f"TOTAL BELANJA : {format_rupiah(total)}")
    print(f"SALDO ANDA    : {format_rupiah(current_user['saldo'])}")

    # Cek saldo
    if current_user["saldo"] < total:
        print("\n❌ Saldo tidak cukup! Pembelian dibatalkan.\n")
        return

    # Kurangi saldo & simpan ke database
    saldo_baru = current_user["saldo"] - total
    users_col.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"saldo": saldo_baru}}
    )
    current_user["saldo"] = saldo_baru

    # Simpan order ke koleksi orders
    order_doc = {
        "user_id": current_user["_id"],
        "username": current_user["username"],
        "items": pesanan,
        "total": total,
        "created_at": datetime.now(),
    }
    orders_col.insert_one(order_doc)

    print("\n✔ Pembelian berhasil!")
    print(f"Sisa saldo Anda: {format_rupiah(saldo_baru)}\n")
    print("=" * 40)


def cek_saldo():
    global current_user
    if current_user is None:
        print("\n❌ Anda belum login.\n")
        return

    # Refresh saldo terbaru dari DB
    current_user = users_col.find_one({"_id": current_user["_id"]})
    print(f"\nSaldo Anda saat ini: {format_rupiah(current_user['saldo'])}\n")


# ====== FITUR TOP UP SALDO ======
def top_up_saldo():
    global current_user
    if current_user is None:
        print("\n❌ Anda harus login untuk top up saldo.\n")
        return

    # Refresh user dari DB
    current_user = users_col.find_one({"_id": current_user["_id"]})

    print("\n" + "=" * 40)
    print("             TOP UP SALDO")
    print("=" * 40)
    print(f"Saldo saat ini: {format_rupiah(current_user['saldo'])}")

    try:
        jumlah = int(input("Masukkan jumlah top up: "))
    except ValueError:
        print("Jumlah harus berupa angka!\n")
        return

    if jumlah <= 0:
        print("Jumlah top up harus lebih dari 0!\n")
        return

    saldo_baru = current_user["saldo"] + jumlah

    # Update saldo di DB
    users_col.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"saldo": saldo_baru}}
    )
    current_user["saldo"] = saldo_baru

    print(f"\n✔ Top up berhasil sebesar {format_rupiah(jumlah)}")
    print(f"Saldo baru Anda: {format_rupiah(saldo_baru)}\n")


# ====== FITUR RIWAYAT TRANSAKSI ======
def lihat_riwayat_transaksi():
    global current_user
    if current_user is None:
        print("\n❌ Anda harus login untuk melihat riwayat transaksi.\n")
        return

    print("\n" + "=" * 40)
    print(f"      RIWAYAT TRANSAKSI ({current_user['username']})")
    print("=" * 40)

    # Ambil order berdasarkan user_id, urutkan terbaru dulu
    riwayat = orders_col.find(
        {"user_id": current_user["_id"]}
    ).sort("created_at", -1)

    ada_data = False
    for idx, order in enumerate(riwayat, start=1):
        ada_data = True
        print(f"\nTransaksi #{idx}")
        print(f"Tanggal : {format_tanggal(order['created_at'])}")
        print(f"Total   : {format_rupiah(order['total'])}")
        print("Item    :")
        for item in order["items"]:
            print(f" - {item['nama']} x{item['jumlah']} = {format_rupiah(item['subtotal'])}")
        print("-" * 40)

    if not ada_data:
        print("Belum ada transaksi untuk user ini.\n")
    else:
        print("\nAkhir riwayat transaksi.\n")


# ====== MENU UTAMA APLIKASI ======
def main_menu():
    while True:
        print("=" * 40)
        print("        SISTEM TOKO JUS (MongoDB)")
        print("=" * 40)
        print("1. Registrasi")
        print("2. Login")
        print("3. Pesan Jus")
        print("4. Cek Saldo")
        print("5. Logout")
        print("6. Top Up Saldo")
        print("7. Lihat Riwayat Transaksi")
        print("0. Keluar")
        print("=" * 40)

        try:
            pilihan = int(input("Pilih menu: "))
        except ValueError:
            print("Input harus angka!\n")
            continue

        if pilihan == 1:
            registrasi()
        elif pilihan == 2:
            login()
        elif pilihan == 3:
            pesan_jus()
        elif pilihan == 4:
            cek_saldo()
        elif pilihan == 5:
            logout()
        elif pilihan == 6:
            top_up_saldo()
        elif pilihan == 7:
            lihat_riwayat_transaksi()
        elif pilihan == 0:
            print("\nTerima kasih menggunakan sistem toko jus!\n")
            break
        else:
            print("Menu tidak dikenal!\n")


if __name__ == "__main__":
    main_menu()