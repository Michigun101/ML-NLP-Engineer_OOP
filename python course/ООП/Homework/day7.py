import matplotlib
matplotlib.use("Agg")   # ← важно! до импорта pyplot
import matplotlib.pyplot as plt
import os
import csv
import json
from day1 import InvalidOperationError
from day4 import TransactionProcessor
from day5 import AuditLog, RiskAnalyzer
from day6 import create_bank, generate_transactions, process_transactions
class ReportBuilder:
    def __init__(self, bank, audit, analyzer, processor, output_dir="reports"):
        self.bank = bank
        self.audit = audit
        self.analyzer = analyzer
        self.processor = processor
        self.output_dir = output_dir

        os.makedirs(output_dir, exist_ok=True)

    def export_to_json(self, data, filename):
        """Сохранить в JSON"""
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def export_to_csv(self, rows, filename, headers=None):
        """Сохранить в CSV"""
        path = os.path.join(self.output_dir, filename)

        if not rows:
            with open(path, "w", encoding="utf-8", newline="") as f:
                if headers:
                    writer = csv.writer(f)
                    writer.writerow(headers)
            return path

        if headers is None:
            headers = list(rows[0].keys())

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

        return path

    def export_to_txt(self, text, filename):
        """Сохранить строку в текстовый файл."""
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def _format_bank_text(self, data):
        """Текстовое представление отчёта по банку"""
        lines = [
            "=" * 60,
            f"ОТЧЁТ ПО БАНКУ: {data['bank_name']}",
            "=" * 60,
            f"Клиентов:      {data['clients_count']}",
            f"Счетов:        {data['accounts_count']}",
            f"Общий баланс:  {data['total_balance_rub']} RUB",
            "",
            "ТОП-3 КЛИЕНТА:",
        ]
        for i, c in enumerate(data["top_3"], 1):
            lines.append(f"  {i}. {c['full_name']}  {c['total_rub']} RUB")

        lines.append("\nАУДИТ:")
        audit_sum = data["audit_summary"]
        lines.append(f"  Всего событий: {audit_sum['total_events']}")
        lines.append(f"  По уровням:    {audit_sum['by_level']}")
        lines.append(f"  По типам:      {audit_sum['by_type']}")

        return "\n".join(lines)

    def _format_risk_text(self, data):
        """Текстовое представление отчёта по рискам"""
        lines = [
            "=" * 60,
            "ОТЧЁТ ПО РИСКАМ",
            "=" * 60,
            f"Подозрительных событий: {data['suspicious_count']}",
            "",
            "СТАТИСТИКА ОШИБОК:",
        ]
        if data["error_stats"]:
            for err_type, count in data["error_stats"].items():
                lines.append(f"  {err_type}: {count}")
        else:
            lines.append("  Ошибок нет")

        lines.append("\nРИСК-ПРОФИЛИ КЛИЕНТОВ:")
        for c in data["risky_clients"]:
            lines.append(
                f"  {c['full_name']}  "
                f"риск: {c['risk_level']}  "
                f"транзакций: {c['transaction_count']}  "
                f"сумма: {c['total_amount']}"
            )

        return "\n".join(lines)

    def build_client_report(self, client_id, fmt="txt"):
        """Отчёт по клиенту."""
        client = self.bank._get_client(client_id)

        accounts_info = []
        total_rub = 0.0
        for acc_id in client.account_ids:
            acc = self.bank._get_account(acc_id)
            bal_rub = acc._balance * self.processor.rates[acc._currency]
            total_rub += bal_rub
            accounts_info.append({
                "id": acc_id,
                "type": acc.__class__.__name__,
                "balance": acc._balance,
                "currency": acc._currency,
                "balance_rub": round(bal_rub, 2),
                "status": acc._status,
            })

        events = self.audit.get_events(client_id=client_id)
        profile = self.analyzer.get_client_profile(client_id)

        data = {
            "client": {
                "id": client.client_id,
                "full_name": client.full_name,
                "age": client.age,
                "email": client.email,
                "phone": client.phone,
                "status": client.status,
            },
            "accounts": accounts_info,
            "total_rub": round(total_rub, 2),
            "risk_profile": profile,
            "events_count": len(events),
        }

        if fmt == "json":
            path = self.export_to_json(data, f"client_{client_id}.json")
            return path

        if fmt == "txt":
            text = self._format_client_text(data)
            path = self.export_to_txt(text, f"client_{client_id}.txt")
            return path

        raise InvalidOperationError(f'Неизвестный формат: {fmt}')

    def _format_client_text(self, data):
        """Текстовое представление отчёта по клиенту."""
        c = data["client"]
        lines = [
            "=" * 60,
            f"ОТЧЁТ ПО КЛИЕНТУ: {c['full_name']}",
            "=" * 60,
            f"ID:      {c['id']}",
            f"Возраст: {c['age']}",
            f"Email:   {c['email']}",
            f"Телефон: {c['phone']}",
            f"Статус:  {c['status']}",
            "",
            "СЧЕТА:",
        ]
        for acc in data["accounts"]:
            lines.append(
                f"  {acc['type']} ...{acc['id'][-4:]}  "
                f"{acc['balance']} {acc['currency']} "
                f"(≈ {acc['balance_rub']} RUB)  [{acc['status']}]"
            )
        lines.append(f"\nИТОГО: {data['total_rub']} RUB")

        lines.append("\nРИСК-ПРОФИЛЬ:")
        p = data["risk_profile"]
        lines.append(f"  Транзакций:    {p['transaction_count']}")
        lines.append(f"  Получателей:   {p['unique_receivers']}")
        lines.append(f"  Общая сумма:   {p['total_amount']}")
        lines.append(f"  Уровень риска: {p['risk_level']}")

        lines.append(f"\nСобытий в аудите: {data['events_count']}")
        return "\n".join(lines)

    def build_bank_report(self, fmt="txt"):
        """Общий отчёт по банку."""
        clients_info = []
        for client in self.bank._clients.values():
            total_rub = 0.0
            for acc_id in client.account_ids:
                acc = self.bank._get_account(acc_id)
                total_rub += acc._balance * self.processor.rates[acc._currency]

            clients_info.append({
                "client_id": client.client_id,
                "full_name": client.full_name,
                "age": client.age,
                "status": client.status,
                "accounts_count": len(client.account_ids),
                "total_rub": round(total_rub, 2),
            })

        clients_info.sort(key=lambda c: c["total_rub"], reverse=True)

        total_bank_rub = sum(c["total_rub"] for c in clients_info)

        data = {
            "bank_name": self.bank.name,
            "clients_count": len(self.bank._clients),
            "accounts_count": len(self.bank._accounts),
            "total_balance_rub": round(total_bank_rub, 2),
            "clients": clients_info,
            "top_3": clients_info[:3],
            "audit_summary": {
                "total_events": len(self.audit),
                "by_level": self.audit.count_by_level(),
                "by_type": self.audit.count_by_event_type(),
            },
        }

        if fmt == "json":
            return self.export_to_json(data, "bank_report.json")
        if fmt == "txt":
            return self.export_to_txt(self._format_bank_text(data), "bank_report.txt")
        raise InvalidOperationError(f'Неизвестный формат: {fmt}')

    def build_risk_report(self, fmt="txt"):
        """Отчёт по рискам"""
        suspicious = self.audit.get_suspicious()

        risky_clients = []
        for client in self.bank._clients.values():
            profile = self.analyzer.get_client_profile(client.client_id)
            risky_clients.append({
                "client_id": client.client_id,
                "full_name": client.full_name,
                "risk_level": profile["risk_level"],
                "transaction_count": profile["transaction_count"],
                "total_amount": profile["total_amount"],
            })
        risky_clients.sort(
            key=lambda c: {"high": 3, "medium": 2, "low": 1}[c["risk_level"]],
            reverse=True,
        )

        data = {
            "suspicious_events": suspicious,
            "suspicious_count": len(suspicious),
            "error_stats": self.audit.get_error_stats(),
            "risky_clients": risky_clients,
        }

        if fmt == "json":
            return self.export_to_json(data, "risk_report.json")
        if fmt == "txt":
            return self.export_to_txt(self._format_risk_text(data), "risk_report.txt")
        raise InvalidOperationError(f'Неизвестный формат: {fmt}')

    def chart_balance_pie(self, filename="chart_pie.png"):
        """Круговая"""
        labels = []
        values = []

        for client in self.bank._clients.values():
            total = 0.0
            for acc_id in client.account_ids:
                acc = self.bank._get_account(acc_id)
                total += acc._balance * self.processor.rates[acc._currency]
            if total > 0:
                labels.append(client.full_name)
                values.append(total)

        fig, ax = plt.subplots(figsize=(10, 7))
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.set_title("Распределение баланса по клиентам RUB")

        path = os.path.join(self.output_dir, filename)
        plt.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def chart_top_clients_bar(self, filename="chart_bar.png", top_n=5):
        """Столбчатая"""
        data = []
        for client in self.bank._clients.values():
            total = 0.0
            for acc_id in client.account_ids:
                acc = self.bank._get_account(acc_id)
                total += acc._balance * self.processor.rates[acc._currency]
            data.append((client.full_name, total))

        data.sort(key=lambda x: x[1], reverse=True)
        data = data[:top_n]

        names = [d[0] for d in data]
        values = [d[1] for d in data]

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(names, values, color="steelblue")
        ax.set_title(f"Топ-{top_n} клиентов по балансу")
        ax.set_ylabel("Баланс, RUB")
        plt.xticks(rotation=30, ha="right")

        
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{val:,.0f}",
                ha="center", va="bottom", fontsize=9,
            )

        path = os.path.join(self.output_dir, filename)
        plt.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def chart_balance_history(self, filename="chart_history.png"):
        """Граф фактического баланса банка во времени."""
        events = self.audit.get_events(event_type="transaction_completed")

        if not events:
            print("Нет данных для графика истории")
            return None

        events.sort(key=lambda e: e["timestamp"])

        timestamps = []
        balances = []
        for e in events:
            bank_total = e["meta"].get("bank_total")
            if bank_total is None:
                continue
            timestamps.append(e["timestamp"])
            balances.append(bank_total)

        if not balances:
            print("Нет данных о балансе банка")
            return None

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(range(len(balances)), balances, marker="o", color="green")
        ax.set_title("Баланс банка во времени (RUB)")
        ax.set_xlabel("Номер транзакции")
        ax.set_ylabel("Общий баланс, RUB")
        ax.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, filename)
        plt.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path

    def save_charts(self):
        return {
            "pie": self.chart_balance_pie(),
            "bar": self.chart_top_clients_bar(),
            "history": self.chart_balance_history(),
        }

if __name__ == "__main__":

    print("ОТЧЁТЫ И ВИЗУАЛИЗАЦИЯ")

    print("\n  1. Создание банка ")
    bank, client_ids, accounts = create_bank()
    audit = AuditLog(file_path="audit_day7.log")          
    analyzer = RiskAnalyzer(bank, audit)                  
    processor = TransactionProcessor(                     
        bank, analyzer=analyzer, audit=audit,
    )

    print(f"   Банк: {bank.name}")
    print(f"   Клиентов: {len(bank._clients)}")
    print(f"   Счетов:   {len(bank._accounts)}")

    print("\n 2. Транзакции ")
    transactions = generate_transactions(bank, accounts)
    print(f"Сгенерировано: {len(transactions)}")

    print("\n3. Обработка")
    results = process_transactions(bank, transactions, audit, analyzer, processor)
    print(f"   Выполнено:     {len(results['completed'])}")
    print(f"   Упало:         {len(results['failed'])}")
    print(f"   Заблокировано: {len(results['blocked'])}")
    print(f"   Аудит: {audit}")

    print("\n 4. Генерация отчётов ")
    builder = ReportBuilder(bank, audit, analyzer, processor)

    
    p1 = builder.build_client_report(client_ids[0], fmt="txt")
    print(f"  Клиент (txt):  {p1}")

    p2 = builder.build_client_report(client_ids[0], fmt="json")
    print(f"  Клиент (json): {p2}")


    p3 = builder.build_bank_report(fmt="txt")
    print(f"  Банк (txt):    {p3}")

    p4 = builder.build_bank_report(fmt="json")
    print(f"  Банк (json):   {p4}")

    p5 = builder.build_risk_report(fmt="txt")
    print(f"  Риски (txt):   {p5}")

    p6 = builder.build_risk_report(fmt="json")
    print(f"  Риски (json):  {p6}")

    rows = []
    for client in bank._clients.values():
        total = 0.0
        for acc_id in client.account_ids:
            acc = bank._get_account(acc_id)
            total += acc._balance * processor.rates[acc._currency]
        rows.append({
            "client_id": client.client_id,
            "full_name": client.full_name,
            "accounts_count": len(client.account_ids),
            "balance_rub": round(total, 2),
        })
    p7 = builder.export_to_csv(rows, "clients.csv")
    print(f"  Клиенты (csv): {p7}")

    print("\n 5. Сохранение графиков ")
    charts = builder.save_charts()
    for name, path in charts.items():
        if path:
            print(f"  {name}: {path}")
        else:
            print(f"  {name}: нет данных")
