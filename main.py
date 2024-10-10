import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
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

def mask_coordinates(df):
    df['Широта'] = df['Широта'].apply(lambda x: int(x))  # Приведение к целому числу
    df['Долгота'] = df['Долгота'].apply(lambda x: int(x))  # Приведение к целому числу

def perturb_date(df):
    if pd.api.types.is_datetime64_any_dtype(df['Дата и время']):
        df['Дата и время'] = df['Дата и время'].dt.date
    else:
        df['Дата и время'] = pd.to_datetime(df['Дата и время'], errors='coerce').dt.date

# Локальное подавление
def suppress_card_numbers(df):
    df['Номер карты'] = ''

# Агрегирование по количеству товаров в стобцах магазин, категория, бренд
def aggregate_items(df):
    df['Количество товаров'] = df.groupby(['Магазин', 'Категория', 'Бренд'])['Количество товаров'].transform('sum')

    return df

def apply_price_range_per_item(df):
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

def anonymize_data():
    global df  
    if df is None:
        messagebox.showerror("Ошибка", "Сначала загрузите файл.")
        return
    
    mask_coordinates(df)

    perturb_date(df)
    
    suppress_card_numbers(df)
    
    df = apply_price_range_per_item(df)

    aggregate_items(df)

    # Вывод отладочной информации
    print(df[['Магазин', 'Категория', 'Бренд', 'Количество товаров', 'Стоимость за единицу товара']])

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

def find_bad_k_values(k_anonymity_df, k_threshold=1):
    bad_k_values = k_anonymity_df[k_anonymity_df['count'] <= k_threshold]
    if len(bad_k_values) > 5:
        return bad_k_values.head(5)
    return bad_k_values

def check_k_anonymity():
    quasi_identifiers = ['Магазин', 'Широта', 'Долгота', 'Категория', 'Бренд']  
    k_anonymity_df, min_k = calculate_k_anonymity(df, quasi_identifiers)
    
    bad_k_values = find_bad_k_values(k_anonymity_df)
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
