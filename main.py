import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os

df = None

def load_file():
    global df
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xlsm *.xls"), ("CSV files", "*.csv")])
    if file_path:
        try:
            df = pd.read_excel(file_path)
            file_label.config(text=f"Файл загружен: {os.path.basename(file_path)}", fg="black", font=("Arial", 12))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")


# Локальное обобщение
def replace_coordinates_with_city(df):
    coordinates_to_city = {
    (59, 30): "Санкт-Петербург",
    (55, 37): "Москва",
    (48, 2): "Париж",
    (40, -74): "Нью-Йорк"
}
    df['Широта'] = df['Широта'].apply(lambda x: int(x))
    df['Долгота'] = df['Долгота'].apply(lambda x: int(x))

    df['Местоположение'] = df.apply(lambda row: coordinates_to_city.get((row['Широта'], row['Долгота']), 'Неизвестное местоположение'), axis=1)
    latitude_index = df.columns.get_loc('Широта')       
    df.drop(columns=['Широта', 'Долгота'], inplace=True)
    df.insert(latitude_index, 'Местоположение', df.pop('Местоположение'))

    return df

# Агрегирование даты по стобцам магазин, категория, бренд
def aggregate_date_season(df):
    if not pd.api.types.is_datetime64_any_dtype(df['Дата и время']):
        df['Дата и время'] = pd.to_datetime(df['Дата и время'], errors='coerce')

    df['Год'] = df['Дата и время'].dt.year
    df['Месяц'] = df['Дата и время'].dt.month

    def get_season(month):
        if month in [12, 1, 2]:
            return 'Зима'
        elif month in [3, 4, 5]:
            return 'Весна'
        elif month in [6, 7, 8]:
            return 'Лето'
        elif month in [9, 10, 11]:
            return 'Осень'

    df['Сезон'] = df['Месяц'].apply(get_season)
    # Подсчитываем количество транзакций для каждого сезона 
    def aggregate_seasons(group):
        year = group['Год'].iloc[0]  
        # Количество транзакций на каждый сезон 
        season_counts = group['Сезон'].value_counts().to_dict()  
        # Формируем строку вида 'Зима(2)', 'Осень(1)', если есть транзакции в этих сезонах
        seasons_str = ', '.join([f"{season}({count})" for season, count in season_counts.items()])
        return f"{year}, {seasons_str}"

    date_column_index = df.columns.get_loc('Дата и время')

    aggregated = df.groupby(['Магазин', 'Категория', 'Бренд']).apply(aggregate_seasons).reset_index()
    aggregated.columns = ['Магазин', 'Категория', 'Бренд', 'Дата(число транзакций)']

    df = df.merge(aggregated, on=['Магазин', 'Категория', 'Бренд'], how='left')
    df.drop(columns=['Год', 'Месяц', 'Сезон', 'Дата и время'], inplace=True)
    df.insert(date_column_index, 'Дата(число транзакций)', df.pop('Дата(число транзакций)'))

    return df

# Маскеризация
def suppress_card_numbers(df):
    df['Номер карты'] = '*'*16

# Агрегирование количества товаров по стобцам магазин, категория, бренд
def aggregate_items(df):
    df['Количество товаров'] = df.groupby(['Магазин', 'Категория', 'Бренд'])['Количество товаров'].transform('sum')

    return df
# Микро-агрегация по стобцам магазин, категория, бренд
def aggregate_price(df):
    df['Стоимость за единицу'] = df['Стоимость'] / df['Количество товаров']
    df = df.drop(columns=['Стоимость']) # Удаление
    unique_groups = df.groupby(['Магазин', 'Категория', 'Бренд']).agg(
        min_price=('Стоимость за единицу', 'min'),
        max_price=('Стоимость за единицу', 'max')
    ).reset_index()
    df = df.drop(columns=['Стоимость за единицу'])
    unique_groups['Стоимость за единицу товара'] = unique_groups['min_price'].round(2).astype(str) + ' - ' + unique_groups['max_price'].round(2).astype(str)
    df = df.merge(unique_groups[['Магазин', 'Категория', 'Бренд', 'Стоимость за единицу товара']], 
                  on=['Магазин', 'Категория', 'Бренд'], 
                  how='left')

    return df

# Агрегация банков по столбцам Магазин, Категория, Бренд
def aggregate_banks(df):
    def aggregate_banks_in_group(group):
        bank_counts = group['Банк'].value_counts().to_dict()
        banks_str = ', '.join([f"{bank}({count})" for bank, count in bank_counts.items() if count > 0])
        return banks_str
    
    aggregated_banks = df.groupby(['Магазин', 'Категория', 'Бренд']).apply(aggregate_banks_in_group).reset_index()
    aggregated_banks.columns = ['Магазин', 'Категория', 'Бренд', 'Банки(число транзакций)']

    df = df.merge(aggregated_banks, on=['Магазин', 'Категория', 'Бренд'], how='left')
    
    bank_index = df.columns.get_loc('Банк')
    df.drop(columns=['Банк'], inplace=True)
    df.insert(bank_index, 'Банки(число транзакций)', df.pop('Банки(число транзакций)'))
    
    return df

# Агрегация платёжных систем по столбцам Магазин, Категория, Бренд
def aggregate_payment_systems(df):
    def aggregate_payments_in_group(group):
        payment_counts = group['Платежная система'].value_counts().to_dict()
        payment_systems_str = ', '.join([f"{payment}({count})" for payment, count in payment_counts.items() if count > 0])
        return payment_systems_str
    
    aggregated_payments = df.groupby(['Магазин', 'Категория', 'Бренд']).apply(aggregate_payments_in_group).reset_index()
    aggregated_payments.columns = ['Магазин', 'Категория', 'Бренд', 'Платежные системы(число транзакций)']

    df = df.merge(aggregated_payments, on=['Магазин', 'Категория', 'Бренд'], how='left')

    payment_system_index = df.columns.get_loc('Платежная система')
    df.drop(columns=['Платежная система'], inplace=True)
    df.insert(payment_system_index, 'Платежные системы(число транзакций)', df.pop('Платежные системы(число транзакций)'))

    return df


def save_depersonalized_data():
    save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    if save_path:
        df.to_excel(save_path, index=False)
        messagebox.showinfo("Успех", f"Файл сохранен: {os.path.basename(save_path)}")

def depersonalize_data(selected_identifiers):
    global df
    if df is None:
        messagebox.showerror("Ошибка", "Сначала загрузите файл.")
        return
    
    if "Местоположение" in selected_identifiers:
        df = replace_coordinates_with_city(df)

    if "Дата и время" in selected_identifiers:
        df = aggregate_date_season(df)

    if "Номер карты" in selected_identifiers:
        suppress_card_numbers(df)

    if "Стоимость" in selected_identifiers:
        df = aggregate_price(df)

    if "Количество товаров" in selected_identifiers:
        aggregate_items(df)

    if "Банк" in selected_identifiers:
        df = aggregate_banks(df)

    if "Платежная система" in selected_identifiers:
        df = aggregate_payment_systems(df)

    #Отладочная информация
    # print(df[['Местоположение', 'Дата(число транзакций)', 'Номер карты', 
    #           'Банки(число транзакций)', 'Платежные системы(число транзакций)', 
    #           'Количество товаров', 'Стоимость за единицу товара']])

    messagebox.showinfo("Успех", "Обезличивание данных завершено.")
    save_depersonalized_data()

def choose_quasi_identifiers():
    global df
    if df is None:
        messagebox.showerror("Ошибка", "Сначала загрузите файл.")
        return
    
    quasi_identifiers_window = tk.Toplevel(root)
    quasi_identifiers_window.geometry("400x300")
    quasi_identifiers_window.title("Выберите данные для обезличивания (квази-идентификаторы)")

    quasi_identifiers = [
        "Магазин", "Местоположение", "Дата и время", 
        "Категория", "Бренд", "Номер карты", 
        "Банк", "Платежная система", "Количество товаров", "Стоимость"
    ]

    selected_identifiers = {}
    
    for identifier in quasi_identifiers:
        var = tk.BooleanVar()
        chk = tk.Checkbutton(quasi_identifiers_window, text=identifier, variable=var)
        chk.pack(anchor='w')
        selected_identifiers[identifier] = var
    
    def on_confirm():
        chosen_identifiers = [key for key, var in selected_identifiers.items() if var.get()]
        if chosen_identifiers:
            quasi_identifiers_window.destroy() 
            depersonalize_data(chosen_identifiers) 
        else:
            messagebox.showwarning("Предупреждение", "Выберите хотя бы один квази-идентификатор.")

    confirm_button = tk.Button(quasi_identifiers_window, text="Подтвердить", command=on_confirm)
    confirm_button.pack(pady=10)
    

def calculate_k_anonymity(df, quasi_identifiers_k):
    grouped = df.groupby(quasi_identifiers_k).size().reset_index(name='count')
    min_k = grouped['count'].min()
    return grouped, min_k

def find_bad_k_values(k_anonymity_df):
    # Сортировка по возрастанию
    sorted_k_values = k_anonymity_df.drop_duplicates(subset='count').sort_values('count')
    bad_k_values = sorted_k_values.head(5)
    total_rows = k_anonymity_df['count'].sum()
    bad_k_values['percent'] = (bad_k_values['count'] / total_rows * 100).round(3)
    
    return bad_k_values[['count', 'percent']].reset_index(drop=True)
   
def check_k_anonymity():
    global df
    if df is None:
        messagebox.showerror("Ошибка", "Сначала загрузите файл.")
        return
    
    quasi_identifiers_k = list(df.columns)
    k_anonymity_df, min_k = calculate_k_anonymity(df, quasi_identifiers_k)

    if min_k == 1:
        unique_rows = k_anonymity_df[k_anonymity_df['count'] == 1]
        messagebox.showinfo("Уникальные строки", f"Количество уникальных строк: {len(unique_rows)}")
    
    bad_k_values = find_bad_k_values(k_anonymity_df)
    messagebox.showinfo("K-Анонимность", f"Минимальное значение K: {min_k}\n\nПлохие значения K:\n{bad_k_values}")


def quit_program():
    if messagebox.askokcancel("Выход", "Вы действительно хотите завершить программу?"):
        root.destroy()

root = tk.Tk()
root.title("Обезличивание данных и K-Анонимность")
root.geometry("500x250")

file_label = tk.Label(root, text="Загрузите файл для обезличивания")
file_label.pack(pady=5)
load_button = tk.Button(root, text="Загрузить файл", command=load_file)
load_button.pack(pady=10)

file_label = tk.Label(root, text="Файл не загружен")
file_label.pack(pady=5)

depersonalize_button = tk.Button(root, text="Обезличить данные", command=choose_quasi_identifiers)
depersonalize_button.pack(pady=10)

k_anonymity_button = tk.Button(root, text="Проверить K-Анонимность", command=check_k_anonymity)
k_anonymity_button.pack(pady=10)

quit_button = tk.Button(root, text="ВЫЙТИ", command=quit_program, bg="red", fg="white", font=("Arial", 12))
quit_button.pack(pady=10)

root.mainloop()