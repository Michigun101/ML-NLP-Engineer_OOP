import json
from datetime import datetime, timedelta, time

from day1 import InvalidOperationError
from day3 import Bank, Client
from day4 import Transaction, TransactionProcessor   


class AuditLog:
    '''Журнал аудита'''

    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR = 'error'

    ALLOWED_LEVELS = (LEVEL_INFO, LEVEL_WARNING, LEVEL_ERROR)

    def __init__(self, file_path=None):
        '''Создать журнал аудита'''
        if file_path is not None:
            if not isinstance(file_path, str) or not file_path.strip():
                raise InvalidOperationError(f'file_path должен быть непустой строкой, получено {file_path}')
            file_path = file_path.strip()

        self._file_path = file_path
        self._events = []

    def __len__(self):
        '''Количество событий в памяти'''
        return len(self._events)


    def __str__(self):
        counts = self.count_by_level()
        return (
            f'AuditLog(total={len(self._events)}, '
            f"info={counts['info']}, "
            f"warning={counts['warning']}, "
            f"error={counts['error']})"
        )

    def log(self, level, event_type, message,
        client_id=None, transaction_id=None, **meta):
        '''Записать событие в аудит'''
        
        if level not in self.ALLOWED_LEVELS:
            raise InvalidOperationError(f"Недопустимый уровень: {level}. Разрешены: {', '.join(self.ALLOWED_LEVELS)}")
        
        if not isinstance(event_type, str) or not event_type.strip():
            raise InvalidOperationError('event_type должен быть непустой строкой')

        if not isinstance(message, str) or not message.strip():
            raise InvalidOperationError('message должен быть непустой строкой')
        
        event = {
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'level': level,
            'event_type': event_type.strip(),
            'message': message.strip(),
            'client_id': client_id,
            'transaction_id': transaction_id,
            'meta': meta,
        }

        self._events.append(event)

        if self._file_path:
            self._write_to_file(event)

        return event

    def _write_to_file(self, event):
        '''Записать событие в файл'''
        try:
            with open(self._file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except OSError as e:
            print(f'[AuditLog] Ошибка записи в файл: {e}')

    def get_events(self, level=None, client_id=None, event_type=None):
        '''Получить события с фильтрацией'''
        result = []
        for event in self._events:
            if level is not None and event['level'] != level:
                continue
            if client_id is not None and event['client_id'] != client_id:
                continue
            if event_type is not None and event['event_type'] != event_type:
                continue
            result.append(event)
        return result

    def get_suspicious(self):
        return [e for e in self._events
                if e['level'] in (self.LEVEL_WARNING, self.LEVEL_ERROR)]

    def get_error_stats(self):
        '''Статистика ошибок по типам'''
        stats = {}
        for e in self._events:
            if e['level'] != self.LEVEL_ERROR:
                continue
            key = e['meta'].get('error_type', e['event_type'])
            stats[key] = stats.get(key, 0) + 1
        return stats

    def count_by_event_type(self):
        '''Сколько событий каждого типа'''
        counts = {}
        for e in self._events:
            counts[e['event_type']] = counts.get(e['event_type'], 0) + 1
        return counts

    def count_by_level(self):
        '''Вернуть счётчик событий по уровням.'''
        counts = {level: 0 for level in self.ALLOWED_LEVELS}
        for event in self._events:
            counts[event['level']] += 1
        return counts


class RiskAnalyzer:
    
    LARGE_AMOUNT = 100000          
    FREQUENT_COUNT = 3              
    FREQUENT_WINDOW = 60            

    RISK_LOW = 'low'
    RISK_MEDIUM = 'medium'
    RISK_HIGH = 'high'

    def __init__(self, bank, audit_log=None):
        self.bank = bank
        self.audit_log = audit_log
        self._history = {}

    def _check_large_amount(self, transaction):
        '''Крупная сумма'''
        if transaction.amount >= self.LARGE_AMOUNT:
            return (2, f'Крупная сумма: {transaction.amount} {transaction.currency}')
        return (0, None)

    def _check_frequent_operations(self, transaction):
        '''Частые операции'''
        
        if transaction.sender_id is None:
            return (0, None)

        client_id = self._find_client_by_account(transaction.sender_id)
        if client_id is None:
            return (0, None)

        history = self._history.get(client_id, [])
        now = datetime.now()
        window_start = now - timedelta(minutes=self.FREQUENT_WINDOW)

        recent = [trans for ts, trans in history if ts >= window_start]
        if len(recent) >= self.FREQUENT_COUNT:
            return (2, f'Частые операции: {len(recent)} за {self.FREQUENT_WINDOW} мин')
        return (0, None)

    def _find_client_by_account(self, account_id):
        '''Найти client_id по ID счёта.'''
        for client in self.bank._clients.values():
            if account_id in client.account_ids:
                return client.client_id
        return None

    def _check_new_receiver(self, transaction):
        '''Поиск перевода на новый счет'''
        if transaction.transaction_type != Transaction.TYPE_TRANSFER:
            return (0, None)
        if transaction.receiver_id is None:
            return (0, None)

        client_id = self._find_client_by_account(transaction.sender_id)
        if client_id is None:
            return (0, None)

        history = self._history.get(client_id, [])
        for _, past in history:
            if past.receiver_id == transaction.receiver_id:
                return (0, None) # не новый

        return (1, f'Перевод на новый счёт: {transaction.receiver_id}')

    def _check_night_operation(self, transaction):
        '''Операция ночью'''
        created = transaction.created_at.time()
        if time(0, 0) <= created < time(5, 0):
            return (1, f"Ночная операция: {created.strftime('%H:%M')}")
        return (0, None)

    def get_client_profile(self, client_id):
        '''Риск-профиль клиента'''
        history = self._history.get(client_id, [])
        if not history:
            return {
                'transaction_count': 0,
                'unique_receivers': 0,
                'total_amount': 0,
                'risk_level': self.RISK_LOW,
            }

        transactions = [t for _, t in history]
        receivers = {t.receiver_id for t in transactions if t.receiver_id}
        total = sum(t.amount for t in transactions)

        if total >= self.LARGE_AMOUNT or len(transactions) >= self.FREQUENT_COUNT * 2:
            level = self.RISK_HIGH
        elif len(transactions) >= self.FREQUENT_COUNT or total >= self.LARGE_AMOUNT // 2:
            level = self.RISK_MEDIUM
        else:
            level = self.RISK_LOW

        return {
            'transaction_count': len(transactions),
            'unique_receivers': len(receivers),
            'total_amount': total,
            'risk_level': level,
        }

    def analyze(self, transaction):
        '''Анализ транзакции'''
        if not isinstance(transaction, Transaction):
            raise InvalidOperationError( f'Ожидается Transaction, получено {type(transaction).__name__}')

        checks = [
            self._check_large_amount(transaction),
            self._check_frequent_operations(transaction),
            self._check_new_receiver(transaction),
            self._check_night_operation(transaction),
        ]

        score = sum(weight for weight, _ in checks)
        reasons = [reason for _, reason in checks if reason]

        if score >= 3:
            level = self.RISK_HIGH
        elif score >= 1:
            level = self.RISK_MEDIUM
        else:
            level = self.RISK_LOW

        return {
            'level': level,
            'score': score,
            'reasons': reasons,
        }
    
    def register_transaction(self, client_id, transaction):
        '''Запись транзакции в историю клиента'''
        if client_id not in self._history:
            self._history[client_id] = []
        self._history[client_id].append((datetime.now(), transaction))

if __name__ == '__main__':

    print('АУДИТ И РИСК-АНАЛИЗ')
    

    
    print('\n1. Подготовка ')

    bank = Bank('Безопасный Банк')
    c1 = Client('Иванов Иван', 30, 'ivan@mail.ru', '+79991234567', 'pass1')
    id1 = bank.add_client(c1)
    acc1 = bank.open_account(id1, 'basic', balance=1_000_000)
    acc2 = bank.open_account(id1, 'basic', balance=0)
    acc3 = bank.open_account(id1, 'basic', balance=0)

    audit = AuditLog(file_path='audit_day5.log')
    analyzer = RiskAnalyzer(bank, audit)
    processor = TransactionProcessor(bank)

    print(f'Счета: acc1={acc1.account_id}, acc2={acc2.account_id}, acc3={acc3.account_id}')
    print(f'AuditLog: {audit}')

    print('\n2. Создание транзакций')

    transactions = [
        Transaction('transfer', 5000, 'RUB',
                    sender_id=acc1.account_id, receiver_id=acc2.account_id),
        Transaction('transfer', 3000, 'RUB',
                    sender_id=acc1.account_id, receiver_id=acc2.account_id),
        Transaction('transfer', 200_000, 'RUB',
                    sender_id=acc1.account_id, receiver_id=acc3.account_id),
        Transaction('transfer', 100, 'RUB',
                    sender_id=acc1.account_id, receiver_id=acc2.account_id),
        Transaction('transfer', 100, 'RUB',
                    sender_id=acc1.account_id, receiver_id=acc2.account_id),
        Transaction('transfer', 100, 'RUB',
                    sender_id=acc1.account_id, receiver_id=acc2.account_id),
        Transaction('deposit', 1000, 'RUB', receiver_id=acc1.account_id),
        Transaction('transfer', 99_999_999, 'RUB',
                    sender_id=acc2.account_id, receiver_id=acc1.account_id),
    ]

    print(f'Создано: {len(transactions)}')
    for i, t in enumerate(transactions, 1):
        print(f'   {i}. {t.transaction_id}: {t.transaction_type} '
              f'{t.amount} {t.currency}')

    print('\n3. Анализ риска')
    for t in transactions:
        risk = analyzer.analyze(t)
        print(f"{t.transaction_id}: {risk['level']:7s} "
              f"(score={risk['score']}) "
              f"{', '.join(risk['reasons']) if risk['reasons'] else '—'}")

    print('\n4. Выполнение с блокировкой')

    blocked_count = 0
    completed_count = 0
    failed_count = 0

    for t in transactions:
        risk = analyzer.analyze(t)

        if risk['level'] == analyzer.RISK_HIGH:
            t.mark_failed(f'Заблокировано: high risk')
            audit.log('error', 'transaction_blocked',
                      f'Заблокирована: {t.transaction_id}',
                      transaction_id=t.transaction_id,
                      risk_score=risk['score'],
                      reasons=risk['reasons'])
            blocked_count += 1
            print(f'   {t.transaction_id} — заблокирована (high risk)')
            continue

        if risk['level'] == analyzer.RISK_MEDIUM:
            audit.log('warning', 'risk_detected',
                      f'Средний риск: {t.transaction_id}',
                      transaction_id=t.transaction_id,
                      risk_score=risk['score'],
                      reasons=risk['reasons'])

        processor.execute(t)

        if t.status == 'completed':
            audit.log('info', 'transaction_completed',
                      f'Выполнена: {t.transaction_id}',
                      transaction_id=t.transaction_id,
                      amount=t.amount)
            analyzer.register_transaction(id1, t)
            completed_count += 1
            print(f'{t.transaction_id} — выполнена')
        elif t.status == 'failed':
            audit.log('error', 'transaction_failed',
                      f'Упала: {t.failure_reason}',
                      transaction_id=t.transaction_id,
                      error_type='operation_error',
                      error=t.failure_reason)
            failed_count += 1
            print(f'{t.transaction_id} — упала: {t.failure_reason}')

    print(f'\n5. Итоги')
    print(f'   Выполнено:     {completed_count}')
    print(f'   Упало:         {failed_count}')
    print(f'   Заблокировано: {blocked_count}')

    print(f'\n6. Балансы ')
    print(f'   acc1: {acc1._balance} RUB')
    print(f'   acc2: {acc2._balance} RUB')
    print(f'   acc3: {acc3._balance} RUB')

    
    print(f'\n7. Аудит ')
    print(f'   Всего: {len(audit)}')
    print(f'   По уровням: {audit.count_by_level()}')
    print(f'   По типам: {audit.count_by_event_type()}')

    print(f'\n8. Подозрительные события')
    for ev in audit.get_suspicious():
        print(f"   [{ev['level']}] {ev['event_type']}: {ev['message']}")

    print(f'\n9. Статистика ошибок')
    for err_type, count in audit.get_error_stats().items():
        print(f'   {err_type}: {count}')

    print(f'\n10. Риск-профиль клиента')
    profile = analyzer.get_client_profile(id1)
    print(f"   Транзакций:           {profile['transaction_count']}")
    print(f"   Уникальных получателей: {profile['unique_receivers']}")
    print(f"   Общая сумма:          {profile['total_amount']}")
    print(f"   Уровень риска:        {profile['risk_level']}")
