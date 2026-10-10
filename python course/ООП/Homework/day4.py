import uuid
from datetime import datetime,timedelta
import time
from datetime import time as dt_time   


from day1 import (
    InvalidOperationError,
    InsufficientFundsError,
)
from day2 import PremiumAccount
from day3 import Bank, Client

class Transaction:

    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    TYPE_TRANSFER = 'transfer'
    TYPE_DEPOSIT = 'deposit'
    TYPE_WITHDRAWAL = 'withdrawal'
    ALLOWED_TYPES = (TYPE_TRANSFER, TYPE_DEPOSIT, TYPE_WITHDRAWAL)

    PRIORITY_HIGH = 'high'
    PRIORITY_NORMAL = 'normal'

    ALLOWED_CURRENCIES = ('RUB', 'USD', 'EUR', 'KZT', 'CNY')

    def __init__(self, transaction_type, amount, currency,
                 sender_id=None, receiver_id=None,
                 transaction_id=None, priority=None,is_external=False):
        
        if transaction_type not in self.ALLOWED_TYPES:
            raise InvalidOperationError( 
                f'Недопустимый тип транзакции: {transaction_type}. '
                f'Разрешены: {', '.join(self.ALLOWED_TYPES)}'
            )
        self.transaction_type = transaction_type

        if (not isinstance(amount, (int, float))
            or isinstance(amount, bool)
            or amount <= 0):
            raise InvalidOperationError(f'Сумма должна быть положительным числом, получено {amount}')
        self.amount = amount

        if not isinstance(currency, str):
            raise InvalidOperationError(f'Валюта должна быть строкой, получено {type(currency).__name__}')
        currency = currency.strip().upper()
        if currency not in self.ALLOWED_CURRENCIES:
            raise InvalidOperationError(f'Недопустимая валюта: {currency}. Разрешены: {', '.join(self.ALLOWED_CURRENCIES)}')
        self.currency = currency

        if sender_id is not None and (not isinstance(sender_id, str) or not sender_id.strip()):
            raise InvalidOperationError(f'sender_id должен быть непустой строкой, получено {sender_id}')
        if receiver_id is not None and (not isinstance(receiver_id, str) or not receiver_id.strip()):
            raise InvalidOperationError(f'receiver_id должен быть непустой строкой, получено {receiver_id}')

        if transaction_type == self.TYPE_TRANSFER:
            if not sender_id or not receiver_id:
                raise InvalidOperationError('Для transfer нужны и sender_id, и receiver_id')
        elif transaction_type == self.TYPE_DEPOSIT:
            if not receiver_id:
                raise InvalidOperationError('Для deposit нужен receiver_id')
            if sender_id:
                raise InvalidOperationError('Для deposit sender_id должен быть None')
        elif transaction_type == self.TYPE_WITHDRAWAL:
            if not sender_id:
                raise InvalidOperationError('Для withdrawal нужен sender_id')
            if receiver_id:
                raise InvalidOperationError('Для withdrawal receiver_id должен быть None')
        self.sender_id = sender_id.strip() if sender_id else None
        self.receiver_id = receiver_id.strip() if receiver_id else None
        

        if transaction_id is None:
            self.transaction_id = str(uuid.uuid4())[:8]
        else:
            if not isinstance(transaction_id, str) or not transaction_id.strip():
                raise InvalidOperationError('transaction_id должен быть непустой строкой')
            self.transaction_id = transaction_id.strip()

        if priority is None:
            priority = self.PRIORITY_NORMAL
        if priority not in (self.PRIORITY_HIGH, self.PRIORITY_NORMAL):
            raise InvalidOperationError(f'Неизвестный приоритет: {priority}. Разрешены: {self.PRIORITY_HIGH}, {self.PRIORITY_NORMAL}')
        self.priority = priority

        if not isinstance(is_external, bool):
            raise InvalidOperationError(f'is_external должен быть bool, получено {type(is_external).__name__}')
        self.is_external = is_external

        self.fee = 0.0                    
        self.status = self.STATUS_PENDING
        self.failure_reason = None
        self.created_at = datetime.now()
        self.processed_at = None

    def __str__(self):
        short_id = f'...{str(self.transaction_id)[-4:]}'
        sender = f'...{self.sender_id[-4:]}' if self.sender_id else '—'
        receiver = f'...{self.receiver_id[-4:]}' if self.receiver_id else '—'
        return (
            f'Transaction(id={short_id}, '
            f'type={self.transaction_type}, '
            f'amount={self.amount} {self.currency}, '
            f'fee={self.fee}, '
            f'status={self.status}, '
            f'from={sender}, to={receiver})'
        )    

    def mark_completed(self):
        '''Пометить транзакцию выполненной.'''
        if self.status != self.STATUS_PENDING:
            raise InvalidOperationError(f'Нельзя завершить транзакцию в статусе {self.status}. Ожидается: pending')
        self.status = self.STATUS_COMPLETED
        self.processed_at = datetime.now()

    def mark_failed(self, reason):
        '''Пометить транзакцию упавшей с указанием причины.'''
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidOperationError('Причина отказа должна быть непустой строкой')
        if self.status != self.STATUS_PENDING:
            raise InvalidOperationError(f'Нельзя пометить failed транзакцию в статусе {self.status}')
        
        self.status = self.STATUS_FAILED
        self.failure_reason = reason.strip()
        self.processed_at = datetime.now()

    def mark_cancelled(self):
        '''Отменить транзакцию.'''
        if self.status != self.STATUS_PENDING:
            raise InvalidOperationError(f'Нельзя отменить транзакцию в статусе {self.status}. Отменить можно только pending.')
        self.status = self.STATUS_CANCELLED
        self.processed_at = datetime.now()

class TransactionQueue:
    def __init__(self):
        self._high = []              
        self._normal = []            
        self._deferred = []          
        self._cancelled = []   

    def __str__(self):
        return (
            f'TransactionQueue(high={len(self._high)}, '
            f'normal={len(self._normal)}, '
            f'deferred={len(self._deferred)}, '
            f'cancelled={len(self._cancelled)})'
        )   

    def is_empty(self):
        return not self._high and not self._normal


    def __len__(self):
        return len(self._high) + len(self._normal) + len(self._deferred)   

    def _promote_deferred(self):
        '''Переместить готовые отложенные в основные очереди.'''
        now = datetime.now()
        still_deferred = []

        for execute_after, transaction in self._deferred:
            if now >= execute_after:
                if transaction.priority == Transaction.PRIORITY_HIGH:
                    self._high.append(transaction)
                else:
                    self._normal.append(transaction)
            else:
                still_deferred.append((execute_after, transaction))

        self._deferred = still_deferred

    def add(self, transaction):
        '''Добавить транзакцию в очередь по её приоритету.'''
        if not isinstance(transaction, Transaction):
            raise InvalidOperationError(f'Ожидается Transaction, получено {type(transaction).__name__}')
        if transaction.status != Transaction.STATUS_PENDING:
            raise InvalidOperationError(f'Нельзя добавить транзакцию в статусе {transaction.status}.Ожидается: pending')
        if transaction.priority == Transaction.PRIORITY_HIGH:
            self._high.append(transaction)
        else:
            self._normal.append(transaction)

    def get_next(self):
        '''Взять следующую транзакцию'''
        self._promote_deferred()

        if self._high:
            return self._high.pop(0)
        if self._normal:
            return self._normal.pop(0)
        return None

    def cancel(self, transaction_id):
        '''Отменить транзакцию'''
        for queue in (self._high, self._normal):
            for i, t in enumerate(queue):
                if t.transaction_id == transaction_id:
                    t.mark_cancelled()
                    queue.pop(i)
                    self._cancelled.append(t)
                    return t

        for i, (_, t) in enumerate(self._deferred):
            if t.transaction_id == transaction_id:
                t.mark_cancelled()
                self._deferred.pop(i)
                self._cancelled.append(t)
                return t

        raise InvalidOperationError( f'Транзакция {transaction_id} не найдена в очереди')

    def defer(self, transaction_id, execute_after):
        '''Отложить транзакцию до указанного времени.'''
        if not isinstance(execute_after, datetime):
            raise InvalidOperationError(f'execute_after должен быть datetime, получено {type(execute_after).__name__}')
        if execute_after <= datetime.now():
            raise InvalidOperationError(f'execute_after должен быть в будущем, получено {execute_after}')

        for queue in (self._high, self._normal):
            for i, t in enumerate(queue):
                if t.transaction_id == transaction_id:
                    queue.pop(i)
                    self._deferred.append((execute_after, t))
                    return t

        raise InvalidOperationError(f'Транзакция {transaction_id} не найдена для откладывания')

class TransactionProcessor:

    DEFAULT_FEE_RATE = 0.01               
    PREMIUM_FEE_RATE = 0.005              
    MAX_RETRIES = 3                       

    def __init__(self, bank, analyzer=None, audit=None):
        
        if not isinstance(bank, Bank):
            raise InvalidOperationError(f'Ожидается Bank, получено {type(bank).__name__}')
        self.bank = bank
        self.analyzer = analyzer       
        self.audit = audit                  
        self.error_log = []            
        self.rates = {
            'RUB': 1.0,      # через рубль
            'USD': 90.0,     
            'EUR': 100.0,    
            'KZT': 0.2,      
            'CNY': 12.5,     
        }

    def process_all(self, queue):
        '''Обработать все транзакции из очереди.'''
        processed = []
        queue._promote_deferred()
        while not queue.is_empty():
            transaction = queue.get_next()
            if transaction is None:
                break
            self.execute(transaction)
            processed.append(transaction)
        return processed

    def _find_client_id(self, transaction):
        """Найти client_id по счёту отправителя/получателя"""
        account_id = transaction.sender_id or transaction.receiver_id
        if account_id is None:
            return None
        for client in self.bank._clients.values():
            if account_id in client.account_ids:
                return client.client_id
        return None

    def _get_total_balance_rub(self):
        """Общий баланс банка в RUB с конвертацией"""
        return sum(
            acc._balance * self.rates[acc._currency]
            for acc in self.bank._accounts.values()
        )

    def execute(self, transaction):
        if not isinstance(transaction, Transaction):
            raise InvalidOperationError(...)
        if transaction.status != Transaction.STATUS_PENDING:
            raise InvalidOperationError(...)

        try:
            # Ночной запрет
            self.bank._check_working_hours()

            # Проверка риска
            if self.analyzer is not None:
                risk = self.analyzer.analyze(transaction)
                if risk["level"] == self.analyzer.RISK_HIGH:
                    reason = f'Заблокировано: high risk ({", ".join(risk["reasons"])})'
                    transaction.mark_failed(reason)
                    if self.audit is not None:
                        self.audit.log(
                            "error", "transaction_blocked", reason,
                            transaction_id=transaction.transaction_id,
                            client_id=self._find_client_id(transaction),   
                            risk_score=risk["score"],
                            reasons=risk["reasons"],
                        )
                    return

                if risk["level"] == self.analyzer.RISK_MEDIUM and self.audit is not None:
                    self.audit.log(
                        "warning", "risk_detected",
                        f'Средний риск: {transaction.transaction_id}',
                        transaction_id=transaction.transaction_id,
                        client_id=self._find_client_id(transaction),   
                        risk_score=risk["score"],
                        reasons=risk["reasons"],
                    )

            # Расчёт комиссии
            transaction.fee = self._calculate_fee(transaction)

            # Выполнение
            self._execute_with_retry(transaction)
            transaction.mark_completed()

            if self.audit is not None:
                self.audit.log(
                    "info", "transaction_completed",
                    f'Выполнена: {transaction.transaction_id}',
                    transaction_id=transaction.transaction_id,
                    client_id=self._find_client_id(transaction),
                    amount=transaction.amount,
                    currency=transaction.currency,                 
                    transaction_type=transaction.transaction_type, 
                    bank_total=self._get_total_balance_rub(),      
                )

        except Exception as e:
            transaction.fee = 0.0
            transaction.mark_failed(str(e))
            self.error_log.append({
                'transaction_id': transaction.transaction_id,
                'error': str(e),
                'type': type(e).__name__,
            })

            if self.audit is not None:
                self.audit.log(
                    "error", "transaction_failed",
                    f'Не успешно: {e}',
                    transaction_id=transaction.transaction_id,
                    client_id=self._find_client_id(transaction),   
                    error_type=type(e).__name__,
                    error=str(e),
                )

    def _calculate_fee(self, transaction):
        if transaction.transaction_type != Transaction.TYPE_TRANSFER:
            return 0.0

        if not transaction.is_external:
            return 0.0   # внутренний — без комиссии

        sender = self.bank._get_account(transaction.sender_id)
        rate = self.DEFAULT_FEE_RATE
        if isinstance(sender, PremiumAccount):
            rate = self.PREMIUM_FEE_RATE

        return transaction.amount * rate

    def _convert(self, amount, from_currency, to_currency):
        '''Конвертировать сумму из одной валюты в другую.'''
        if from_currency == to_currency:
            return amount

        if from_currency not in self.rates or to_currency not in self.rates:
            raise InvalidOperationError(f'Нет курса для перевода из {from_currency} в {to_currency}')

        amount_in_rub = amount * self.rates[from_currency]
        return amount_in_rub / self.rates[to_currency]

    def _execute_with_retry(self, transaction):
        '''Повторные попытки'''
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self._dispatch(transaction)
                return
            except (InsufficientFundsError, InvalidOperationError):
                raise    # бизнес-ошибки — сразу
            except Exception:
                if attempt == self.MAX_RETRIES:
                    raise
                continue

    def _dispatch(self, transaction):
        '''Направить транзакцию в нужный обработчик.'''
        if transaction.transaction_type == Transaction.TYPE_TRANSFER:
            self._execute_transfer(transaction)
        elif transaction.transaction_type == Transaction.TYPE_DEPOSIT:
            self._execute_deposit(transaction)
        elif transaction.transaction_type == Transaction.TYPE_WITHDRAWAL:
            self._execute_withdrawal(transaction)

    def _execute_deposit(self, transaction):
        '''Пополнение счёта.'''
        account = self.bank._get_account(transaction.receiver_id)

        if account._currency != transaction.currency:
            amount = self._convert(
                transaction.amount,
                transaction.currency,
                account._currency,
            )
        else:
            amount = transaction.amount

        account.deposit(amount)

    def _execute_withdrawal(self, transaction):
        '''Снятие со счёта.'''
        account = self.bank._get_account(transaction.sender_id)

        if account._currency != transaction.currency:
            amount = self._convert(
                transaction.amount,
                transaction.currency,
                account._currency,
            )
        else:
            amount = transaction.amount

        if not isinstance(account, PremiumAccount):
            if account._balance - amount < 0:
                raise InsufficientFundsError(
                    f'Нельзя уйти в минус (счёт {account.account_id}). '
                    f'Баланс: {account._balance}, снятие: {amount}'
                )

        account.withdraw(amount)

    def _execute_transfer(self, transaction):
        """Перевод между счетами с корректной конвертацией валют"""
        sender = self.bank._get_account(transaction.sender_id)
        receiver = self.bank._get_account(transaction.receiver_id)

        fee_in_tx_currency = transaction.fee

        # Приводим сумму и комиссию к валюте списания
        amount_in_sender_currency = self._convert(
            transaction.amount,
            transaction.currency,         
            sender._currency,             
        )
        fee_in_sender_currency = self._convert(
            fee_in_tx_currency,
            transaction.currency,
            sender._currency,
        )

        total_from_sender = amount_in_sender_currency + fee_in_sender_currency

        # Сумма для зачисления в валюте счёта получателя
        received = self._convert(
            transaction.amount,
            transaction.currency,
            receiver._currency,
        )

        if not isinstance(sender, PremiumAccount):
            if sender._balance - total_from_sender < 0:
                raise InsufficientFundsError(
                    f'Недостаточно средств: баланс {sender._balance} {sender._currency}, '
                    f'нужно {total_from_sender:.2f} {sender._currency} '
                    f'(включая комиссию {fee_in_sender_currency:.2f} {sender._currency})'
                )

        # Проверка получателя
        if receiver._status != 'active':
            raise InvalidOperationError(
                f'Счёт получателя {receiver.account_id} не активен: {receiver._status}'
            )

        sender.withdraw(total_from_sender)
        receiver.deposit(received)

    
if __name__ == '__main__':
    Bank._allow_operations_24h = True
    print()
    print('СИСТЕМА ТРАНЗАКЦИЙ')
    print()

    print('1. Подготовка банка и счетов/n')

    bank = Bank('Транзакционный Банк')

    c1 = Client('Иванов Иван', 30, 'ivan@mail.ru', '+79991234567', 'pass123')
    c2 = Client('Петров Пётр', 25, 'petr@mail.ru', '+79997654321', 'pass456')
    c3 = Client('Сидоров Сидор', 35, 'sidor@mail.ru', '+79990000000', 'pass789')

    id1 = bank.add_client(c1)
    id2 = bank.add_client(c2)
    id3 = bank.add_client(c3)

    # Счета разных типов
    acc1 = bank.open_account(id1, 'basic', balance=10000)            
    acc2 = bank.open_account(id1, 'savings', balance=5000, min_balance=1000)  
    acc3 = bank.open_account(id2, 'premium', balance=20000, overdraft_limit=5000, operation_fee=50)  
    acc4 = bank.open_account(id3, 'basic', balance=3000)               
    acc_usd = bank.open_account(id3, 'basic', balance=1000, currency='USD')

    print(f'   acc1 (basic RUB):        {acc1.account_id} — {acc1._balance} RUB')
    print(f'   acc2 (savings RUB):      {acc2.account_id} — {acc2._balance} RUB')
    print(f'   acc3 (premium RUB):      {acc3.account_id} — {acc3._balance} RUB')
    print(f'   acc4 (basic RUB):        {acc4.account_id} — {acc4._balance} RUB')
    print(f'   acc_usd (basic USD):     {acc_usd.account_id} — {acc_usd._balance} USD')

    print('\n2. Создание 10 транзакций ')

    transactions = []

    # 1. Обычный перевод basic - basic
    t1 = Transaction('transfer', 500, 'RUB',
                     sender_id=acc1.account_id,
                     receiver_id=acc4.account_id,
                     is_external=True )
    transactions.append(t1)

    # 2. Перевод от премиум аккаунта
    t2 = Transaction('transfer', 1000, 'RUB',
                     sender_id=acc3.account_id,
                     receiver_id=acc1.account_id,
                     is_external=True)
    transactions.append(t2)

    # 3. Пополнение счёта
    t3 = Transaction('deposit', 2000, 'RUB',
                     receiver_id=acc2.account_id)
    transactions.append(t3)

    # 4. Снятие со счёта
    t4 = Transaction('withdrawal', 300, 'RUB',
                     sender_id=acc4.account_id)
    transactions.append(t4)

    # 5. Перевод в USD 
    t5 = Transaction('transfer', 1000, 'RUB',
                     sender_id=acc1.account_id,
                     receiver_id=acc_usd.account_id,
                     is_external=True)
    transactions.append(t5)

    # 6. Пополнение в USD
    t6 = Transaction('deposit', 200, 'USD',
                     receiver_id=acc_usd.account_id)
    transactions.append(t6)

    # 7. Недостаточно средств 
    t7 = Transaction('transfer', 999999, 'RUB',
                     sender_id=acc4.account_id,
                     receiver_id=acc1.account_id,
                     is_external=True)
    transactions.append(t7)

    # 8. Перевод с высоким приоритетом
    t8 = Transaction('transfer', 100, 'RUB',
                     sender_id=acc1.account_id,
                     receiver_id=acc2.account_id,
                     priority='high')
    transactions.append(t8)

    # 9. Перевод на замороженный счёт 
    bank.freeze_account(acc2.account_id)
    t9 = Transaction('transfer', 100, 'RUB',
                     sender_id=acc1.account_id,
                     receiver_id=acc2.account_id)
    transactions.append(t9)
    bank.unfreeze_account(acc2.account_id)   

    # 10. Обычный deposit на acc1 
    t10 = Transaction('deposit', 5000, 'RUB',
                      receiver_id=acc1.account_id)
    transactions.append(t10)

    print(f'Создано транзакций: {len(transactions)}')
    for i, t in enumerate(transactions, 1):
        print(f'   {i}. {t}')


    print('\n3. Работа с очередью ')

    queue = TransactionQueue()

    for t in transactions[:-1]:
        queue.add(t)

    print(f'Добавлено 9 транзакций: {queue}')

    # Отменим t3 
    cancelled = queue.cancel(t3.transaction_id)
    print(f'Отменена t3: {cancelled.transaction_id}, status={cancelled.status}')

    # Отложим t10 на 2 секунды
    execute_after = datetime.now() + timedelta(seconds=2)
    queue.add(t10)
    queue.defer(t10.transaction_id, execute_after)
    print(f't10 отложена до {execute_after.strftime('%H:%M:%S')}')
    print(f'Очередь: {queue}')

    
    print('\n4. Обработка очереди ')

    processor = TransactionProcessor(bank)
    print(f'Процессор создан')

    processed = processor.process_all(queue)
    print(f'Обработано: {len(processed)}')


    print('\n5. Результаты транзакций ')

    for t in transactions:
        status_icon = 'good' if t.status == 'completed' else 'not good' if t.status == 'failed' else 'ok'
        fee_str = f', fee={t.fee:.2f}' if t.fee > 0 else ''
        reason = f' — {t.failure_reason}' if t.failure_reason else ''
        print(f'{status_icon} {t.transaction_id}: {t.transaction_type} '
              f'{t.amount} {t.currency} - {t.status}{fee_str}{reason}')

    print('\n6. Балансы счетов ')
    print(f'acc1 (basic RUB):   {acc1._balance} RUB')
    print(f'acc2 (savings RUB): {acc2._balance} RUB')
    print(f'acc3 (premium RUB): {acc3._balance} RUB')
    print(f'acc4 (basic RUB):   {acc4._balance} RUB')
    print(f'acc_usd (USD):      {acc_usd._balance} USD')

    print(f'\n7. Лог ошибок ({len(processor.error_log)}) ')
    for err in processor.error_log:
        print(f'  {err['transaction_id']} [{err['type']}]: {err['error']}')


    print(f'\n8. Ждём отложенную t10 ')
    print(f'   Очередь после обработки: {queue}')

    if len(queue) > 0:
        print(f'Ждем 3 секунды...')
        time.sleep(3)

        processed2 = processor.process_all(queue)
        print(f'Обработано отложенных: {len(processed2)}')
        for t in processed2:
            print(f'   {t.transaction_id}: {t.status}')

        print(f'   acc1 после отложенной: {acc1._balance} RUB')

    print('\n9. ТЕСТ ВАЛЮТНЫХ ПЕРЕВОДОВ')

    acc_rub = bank.open_account(id1, 'basic', balance=10000)              # RUB
    acc_usd2 = bank.open_account(id1, 'basic', balance=1000, currency='USD')

    print(f'   acc_rub: {acc_rub._balance} RUB')
    print(f'   acc_usd2: {acc_usd2._balance} USD')

    t_rub_to_usd = Transaction('transfer', 9000, 'RUB',
                            sender_id=acc_rub.account_id,
                            receiver_id=acc_usd2.account_id)
    queue2 = TransactionQueue()
    queue2.add(t_rub_to_usd)
    processor.process_all(queue2)

    print(f'   После перевода 9000 RUB -> USD:')
    print(f'     acc_rub:  {acc_rub._balance} RUB')
    print(f'     acc_usd2: {acc_usd2._balance} USD')

    t_usd_to_usd = Transaction('transfer', 5000, 'RUB',
                            sender_id=acc_usd2.account_id,
                            receiver_id=acc_usd2.account_id)  

    print()

    print('\n10. ТЕСТ ВНУТРЕННИХ vs ВНЕШНИХ ПЕРЕВОДОВ')

    t_internal = Transaction(
        'transfer', 1000, 'RUB',
        sender_id=acc1.account_id,
        receiver_id=acc2.account_id,
    )
    fee_internal = processor._calculate_fee(t_internal)
    print(f'   Внутренний (acc1 -> acc2, один клиент): fee={fee_internal}')

    t_external = Transaction(
        'transfer', 1000, 'RUB',
        sender_id=acc1.account_id,
        receiver_id=acc3.account_id,
        is_external=True,   
    )
    fee_external = processor._calculate_fee(t_external)
    print(f'   Внешний (acc1 -> acc3, разные клиенты): fee={fee_external}')

    t_premium = Transaction(
        'transfer', 1000, 'RUB',
        sender_id=acc3.account_id,
        receiver_id=acc1.account_id,
        is_external=True,   
    )
    fee_premium = processor._calculate_fee(t_premium)
    print(f'   Внешний от премиум (acc3 -> acc1): fee={fee_premium}')

    print('\n11. ТЕСТ НОЧНОГО ЗАПРЕТА')

    bank_check = Bank("NightTestBank")
    c_night = Client("Ночной Клиент", 30, "night@mail.ru", "+79991111111", "pass")
    id_night = bank_check.add_client(c_night)

    try:
        bank_check._check_working_hours(current_time=dt_time(2, 0))
        print(' 02:00 — не упало')
    except InvalidOperationError as e:
        print(f' 02:00 — запрет: {e}')

    try:
        bank_check._check_working_hours(current_time=dt_time(10, 0))
        print(' 10:00 — работает')
    except InvalidOperationError as e:
        print(f' 10:00 — упало: {e}')

    Bank._allow_operations_24h = False   
    processor_night = TransactionProcessor(bank_check)
    acc_night = bank_check.open_account(id_night, 'basic', balance=1000)

    original_check = bank_check._check_working_hours
    bank_check._check_working_hours = lambda current_time=None: original_check(current_time=dt_time(2, 0))

    t_night = Transaction('deposit', 500, 'RUB', receiver_id=acc_night.account_id)
    processor_night.execute(t_night)

    print(f' Ночная транзакция: status={t_night.status}, reason={t_night.failure_reason}')


    bank_check._check_working_hours = original_check
    Bank._allow_operations_24h = True