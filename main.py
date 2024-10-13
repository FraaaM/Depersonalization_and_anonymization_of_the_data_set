import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os

def load_file():
    global df
    file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    if file_path:
        try:
            df = pd.read_excel(file_path)
            file_label.config(text=f"Файл загружен: {os.path.basename(file_path)}")
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

# Аргегация банков и п.с. по столбцам Магазин, Категория, Бренд
def aggregate_bank_and_payment_system(df):

    def aggregate_banks(group):
        # Подсчитываем количество каждого банка в группе
        bank_counts = group['Банк'].value_counts().to_dict()  
        # Создаем строку вида 'Банк(число транзакций)'
        banks_str = ', '.join([f"{bank}({count})" for bank, count in bank_counts.items() if count > 0])  
        return banks_str

    def aggregate_payment_systems(group):
        payment_counts = group['Платежная система'].value_counts().to_dict()  
        payment_systems_str = ', '.join([f"{payment}({count})" for payment, count in payment_counts.items() if count > 0]) 
        return payment_systems_str

    aggregated_banks = df.groupby(['Магазин', 'Категория', 'Бренд']).apply(aggregate_banks).reset_index()
    aggregated_banks.columns = ['Магазин', 'Категория', 'Бренд', 'Банки(число транзакций)']
    
    aggregated_payments = df.groupby(['Магазин', 'Категория', 'Бренд']).apply(aggregate_payment_systems).reset_index()
    aggregated_payments.columns = ['Магазин', 'Категория', 'Бренд', 'Платежные системы(число транзакций)']
    
    df = df.merge(aggregated_banks, on=['Магазин', 'Категория', 'Бренд'], how='left')
    df = df.merge(aggregated_payments, on=['Магазин', 'Категория', 'Бренд'], how='left')

    bank_index = df.columns.get_loc('Банк')
    payment_system_index = df.columns.get_loc('Платежная система')
    df.drop(columns=['Банк', 'Платежная система'], inplace=True)

    df.insert(bank_index, 'Банки(число транзакций)', df.pop('Банки(число транзакций)'))
    df.insert(payment_system_index, 'Платежные системы(число транзакций)', df.pop('Платежные системы(число транзакций)'))

    return df

def anonymize_data():
    global df  
    if df is None:
        messagebox.showerror("Ошибка", "Сначала загрузите файл.")
        return
    
    df = replace_coordinates_with_city(df)

    df = aggregate_date_season(df)
    
    suppress_card_numbers(df)
    
    df = aggregate_price(df)

    aggregate_items(df)

    df = aggregate_bank_and_payment_system(df)

    # Вывод отладочной информации
    print(df[['Местоположение','Дата(число транзакций)','Номер карты','Банки(число транзакций)','Платежные системы(число транзакций)','Количество товаров','Стоимость за единицу товара']])

    messagebox.showinfo("Успех", "Обезличивание данных завершено.")
    
    save_anonymized_data()

def save_anonymized_data():
    save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    if save_path:
        df.to_excel(save_path, index=False)
        messagebox.showinfo("Успех", f"Файл сохранен: {os.path.basename(save_path)}")

def calculate_k_anonymity(df, quasi_identifiers):
    grouped = df.groupby(quasi_identifiers).size().reset_index(name='count')
    min_k = grouped['count'].min()
    return grouped, min_k

def find_bad_k_values(k_anonymity_df):
    # Сортировка по возрастанию
    sorted_k_values = k_anonymity_df.drop_duplicates(subset='count').sort_values('count')
    bad_k_values = sorted_k_values.head(5)
    total_rows = k_anonymity_df['count'].sum()
    bad_k_values['percent'] = (bad_k_values['count'] / total_rows * 100).round(2)
    
    return bad_k_values[['count', 'percent']]

def check_k_anonymity():
    quasi_identifiers = ['Магазин','Местоположение','Дата(число транзакций)','Категория', 'Бренд','Номер карты','Банки(число транзакций)','Платежные системы(число транзакций)','Количество товаров','Стоимость за единицу товара']  
    k_anonymity_df, min_k = calculate_k_anonymity(df, quasi_identifiers)
    
    bad_k_values = find_bad_k_values(k_anonymity_df)
    messagebox.showinfo("K-Анонимность", f"Использующиеся столбцы {quasi_identifiers}")
    messagebox.showinfo("K-Анонимность", f"Минимальное значение K: {min_k}\n\nПлохие значения K:\n{bad_k_values}")

    if min_k == 1:
        unique_rows = k_anonymity_df[k_anonymity_df['count'] == 1]
        messagebox.showinfo("Уникальные строки", f"Количество уникальных строк: {len(unique_rows)}")

root = tk.Tk()
root.title("Обезличивание данных и K-Анонимность")

load_button = tk.Button(root, text="Загрузить файл", command=load_file)
load_button.pack(pady=10)

file_label = tk.Label(root, text="Файл не загружен")
file_label.pack(pady=5)

anonymize_button = tk.Button(root, text="Обезличить данные", command=anonymize_data)
anonymize_button.pack(pady=10)

k_anonymity_button = tk.Button(root, text="Проверить K-Анонимность", command=check_k_anonymity)
k_anonymity_button.pack(pady=10)

root.mainloop()