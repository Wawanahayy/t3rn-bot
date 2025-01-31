# Mengimpor pustaka Web3
from web3 import Web3
from eth_account import Account
import time
import sys
import os
import random  # Mengimpor modul acak

# Konfigurasi jembatan data
from data_bridge import data_bridge
from keys_and_addresses import private_keys, labels  # Tidak lagi membaca my_addresses
from network_config import networks

# Fungsi untuk membuat teks menjadi rata tengah
def center_text(text):
    terminal_width = os.get_terminal_size().columns
    lines = text.splitlines()
    centered_lines = [line.center(terminal_width) for line in lines]
    return "\n".join(centered_lines)

# Fungsi untuk membersihkan terminal
def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

description = """
Bot Jembatan Otomatis  https://bridge.t1rn.io/
Sialan Rambeboy, mencuri kunci pribadi🐶
"""

# Warna dan simbol untuk setiap rantai
chain_symbols = {
    'Base': '\033[34m',  # Warna untuk rantai Base
    'OP Sepolia': '\033[91m',
}

# Definisi warna
green_color = '\033[92m'
reset_color = '\033[0m'
menu_color = '\033[95m'  # Warna teks menu

# URL penjelajah blok untuk setiap jaringan
explorer_urls = {
    'Base': 'https://sepolia.base.org',
    'OP Sepolia': 'https://sepolia-optimism.etherscan.io/tx/',
    'BRN': 'https://brn.explorer.caldera.xyz/tx/'
}

# Fungsi untuk mendapatkan saldo BRN
def get_brn_balance(web3, my_address):
    balance = web3.eth.get_balance(my_address)
    return web3.from_wei(balance, 'ether')

# Fungsi untuk memeriksa saldo rantai
def check_balance(web3, my_address):
    balance = web3.eth.get_balance(my_address)
    return web3.from_wei(balance, 'ether')

# Fungsi untuk membuat dan mengirim transaksi
def send_bridge_transaction(web3, account, my_address, data, network_name):
    nonce = web3.eth.get_transaction_count(my_address, 'pending')
    value_in_ether = 0.4
    value_in_wei = web3.to_wei(value_in_ether, 'ether')

    try:
        gas_estimate = web3.eth.estimate_gas({
            'to': networks[network_name]['contract_address'],
            'from': my_address,
            'data': data,
            'value': value_in_wei
        })
        gas_limit = gas_estimate + 50000  # Tambahan margin keamanan
    except Exception as e:
        print(f"Kesalahan dalam estimasi gas: {e}")
        return None

    base_fee = web3.eth.get_block('latest')['baseFeePerGas']
    priority_fee = web3.to_wei(5, 'gwei')
    max_fee = base_fee + priority_fee

    transaction = {
        'nonce': nonce,
        'to': networks[network_name]['contract_address'],
        'value': value_in_wei,
        'gas': gas_limit,
        'maxFeePerGas': max_fee,
        'maxPriorityFeePerGas': priority_fee,
        'chainId': networks[network_name]['chain_id'],
        'data': data
    }

    try:
        signed_txn = web3.eth.account.sign_transaction(transaction, account.key)
    except Exception as e:
        print(f"Kesalahan dalam penandatanganan transaksi: {e}")
        return None

    try:
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        # Mendapatkan saldo terbaru
        balance = web3.eth.get_balance(my_address)
        formatted_balance = web3.from_wei(balance, 'ether')

        # Mendapatkan tautan ke penjelajah blok
        explorer_link = f"{explorer_urls[network_name]}{web3.to_hex(tx_hash)}"

        # Menampilkan informasi transaksi
        print(f"{green_color}📤 Alamat pengirim: {account.address}")
        print(f"⛽ Gas yang digunakan: {tx_receipt['gasUsed']}")
        print(f"🗳️  Nomor blok: {tx_receipt['blockNumber']}")
        print(f"💰 Saldo ETH: {formatted_balance} ETH")
        brn_balance = get_brn_balance(Web3(Web3.HTTPProvider('https://brn.rpc.caldera.xyz/http')), my_address)
        print(f"🔵 Saldo BRN: {brn_balance} BRN")
        print(f"🔗 Tautan ke penjelajah blok: {explorer_link}\n{reset_color}")

        return web3.to_hex(tx_hash), value_in_ether
    except Exception as e:
        print(f"Kesalahan dalam mengirim transaksi: {e}")
        return None, None

# Fungsi untuk memproses transaksi di jaringan tertentu
def process_network_transactions(network_name, bridges, chain_data, successful_txs):
    web3 = Web3(Web3.HTTPProvider(chain_data['rpc_url']))

    # Jika tidak dapat terhubung, coba kembali hingga berhasil
    while not web3.is_connected():
        print(f"Tidak dapat terhubung ke {network_name}, mencoba kembali...")
        time.sleep(5)  # Tunggu 5 detik sebelum mencoba lagi
        web3 = Web3(Web3.HTTPProvider(chain_data['rpc_url']))
    
    print(f"Berhasil terhubung ke {network_name}")

    for bridge in bridges:
        for i, private_key in enumerate(private_keys):
            account = Account.from_key(private_key)

            # Menghasilkan alamat dari kunci pribadi
            my_address = account.address

            data = data_bridge.get(bridge)
            if not data:
                print(f"Data untuk jembatan {bridge} tidak tersedia!")
                continue

            result = send_bridge_transaction(web3, account, my_address, data, network_name)
            if result:
                tx_hash, value_sent = result
                successful_txs += 1

                if value_sent is not None:
                    print(f"{chain_symbols[network_name]}🚀 Total transaksi sukses: {successful_txs} | {labels[i]} | Jembatan: {bridge} | Jumlah: {value_sent:.5f} ETH ✅{reset_color}\n")
                else:
                    print(f"{chain_symbols[network_name]}🚀 Total transaksi sukses: {successful_txs} | {labels[i]} | Jembatan: {bridge} ✅{reset_color}\n")

                print(f"{'='*150}")
                print("\n")
            
            # Menunggu antara 120 hingga 180 detik secara acak
            wait_time = random.uniform(120, 180)
            print(f"⏳ Menunggu {wait_time:.2f} detik sebelum lanjut...\n")
            time.sleep(wait_time)

    return successful_txs


# Fungsi untuk meminta input jumlah bridge
def get_amount_input():
    try:
        amount = float(input("Masukkan jumlah ETH yang ingin di-bridge (contoh: 0.4): "))
        if amount <= 0:
            print("Jumlah harus lebih besar dari 0. Coba lagi.")
            return get_amount_input()  # Meminta input lagi jika jumlah tidak valid
        return amount
    except ValueError:
        print("Input tidak valid. Harap masukkan angka.")
        return get_amount_input()

    # Warna dan simbol untuk setiap rantai
# Warna dan simbol untuk setiap rantai
chain_symbols = {
    'Base': '\033[34m',  # Warna untuk rantai Base
    'OP Sepolia': '\033[91m',
    'Arbitrum Sepolia': '\033[92m',  # Menambahkan warna untuk Arbitrum Sepolia
    'blast sepolia': '\033[93m',  # Menambahkan warna untuk L1RN
}

# Fungsi untuk menampilkan menu jaringan dan memilih dengan angka
def display_network_menu():
    print(f"{menu_color}Pilih jaringan asal untuk menjalankan transaksi:{reset_color}")
    print(" ")
    
    # Menampilkan jaringan dengan nomor pilihan
    networks_list = list(networks.items())
    for idx, (key, network) in enumerate(networks_list, 1):
        print(f"{chain_symbols.get(key, reset_color)}{idx}. {key}{reset_color}")
    
    print(" ")
    # Meminta input angka untuk memilih jaringan
    try:
        choice = int(input("Masukkan nomor jaringan yang ingin dipilih: "))
        if 1 <= choice <= len(networks):
            return networks_list[choice - 1][0]  # Mengembalikan nama jaringan berdasarkan nomor yang dipilih
        else:
            print("Pilihan tidak valid. Coba lagi.")
            return display_network_menu()  # Meminta input lagi jika pilihan tidak valid
    except ValueError:
        print("Input tidak valid. Harap masukkan angka.")
        return display_network_menu()  # Meminta input lagi jika input bukan angka

# Fungsi utama untuk menjalankan skrip
def main():
    print("\033[92m" + center_text(description) + "\033[0m")
    print("\n\n")

    successful_txs = 0
    current_network = display_network_menu()  # Memilih jaringan berdasarkan nomor

    if not current_network:
        print("Jaringan tidak ditemukan.")
        return

    while True:
        amount_to_bridge = get_amount_input()  # Meminta input jumlah untuk bridge

        # Menghubungkan ke Web3 dan memeriksa saldo
        web3 = Web3(Web3.HTTPProvider(networks[current_network]['rpc_url']))

        while not web3.is_connected():
            print(f"Tidak dapat terhubung ke {current_network}, mencoba kembali...")
            time.sleep(5)
            web3 = Web3(Web3.HTTPProvider(networks[current_network]['rpc_url']))

        print(f"Berhasil terhubung ke {current_network}")

        my_address = Account.from_key(private_keys[0]).address
        balance = check_balance(web3, my_address)

        # Memeriksa saldo sebelum melanjutkan transaksi
        if balance < amount_to_bridge:
            print(f"{chain_symbols[current_network]}Saldo {current_network} kurang dari {amount_to_bridge} ETH, beralih ke jaringan lain.")
            # Beralih ke jaringan lain atau lakukan tindakan lain

        successful_txs = process_network_transactions(current_network, ["Base - OP Sepolia", "Arbitrum Sepolia"], networks[current_network], successful_txs)

        time.sleep(random.uniform(30, 60))

if __name__ == "__main__":
    main()
