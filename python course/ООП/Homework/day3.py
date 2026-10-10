import re
import uuid
from datetime import datetime, time   # для Bank пригодится

from day1 import (
    BankAccount,
    InvalidOperationError,
    InsufficientFundsError,
    AccountFrozenError,
    AccountClosedError,
)
from day2 import SavingsAccount, PremiumAccount, InvestmentAccount

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_PATTERN = re.compile(r'^[\+\d\s\-\(\)\.]+$')

class Client:

    STATUS_ACTIVE = 'active'
    STATUS_BLOCKED = 'blocked'
    STATUS_SUSPICIOUS = 'suspicious'

    def __init__(self, full_name, age, email, phone, password,client_id=None):

        if not isinstance(full_name, str) or not full_name.strip():
            raise InvalidOperationError(
                'ФИО должно быть непустой строкой'
            )
        self.full_name = full_name.strip()

        if not isinstance(age, int) or isinstance(age, bool):
            raise InvalidOperationError(
                f'Возраст клиента должен быть целочисленным, получено {age}'
            )
        if age < 18:
            raise InvalidOperationError(
                f'Клиент должен быть старше 18 лет, получено {age}'
            )
        self.age = age

        if not isinstance(email, str):
            raise InvalidOperationError(
                f'Email должен быть строкой, получено {type(email).__name__}'
            )
        email = email.strip()
        if not EMAIL_REGEX.match(email):
            raise InvalidOperationError(f'Некорректный email: {email}')
        self.email = email

        if not isinstance(phone, str):
            raise InvalidOperationError(
                f'Телефон должен быть строкой, получено {type(phone).__name__}'
            )
        
        if not PHONE_PATTERN.match(phone):
            raise InvalidOperationError(
                f'Телефон содержит недопустимые символы: {phone}. '
                f'Разрешены: цифры, +, -, пробелы, скобки, точки'
            )
        digits = re.sub(r'\D', '', phone)   
        if not (10 <= len(digits) <= 15):
            raise InvalidOperationError(
                f'Телефон должен содержать 10–15 цифр, получено {len(digits)}: {phone}'
            )
        self.phone = phone.strip()

        if not isinstance(password, str) or len(password) < 4:
            raise InvalidOperationError('Пароль должен быть строкой минимум из 4 символов')
            
        
        self.password = password

        if client_id is None:
            self.client_id = str(uuid.uuid4())[:8]
        else:
            if not isinstance(client_id, str) or not client_id.strip():
                raise InvalidOperationError(
                    'ID должен быть непустой строкой'
                )
            self.client_id = client_id.strip()

        self.status = self.STATUS_ACTIVE
        self.account_ids = []
        self.failed_attempts = 0
        self.suspicious_actions = []

    def add_account(self, account_id):
        '''Добавить ID счёта к клиенту.'''
        if not isinstance(account_id, str) or not account_id.strip():
            raise InvalidOperationError('account_id должен быть непустой строкой')
        if account_id in self.account_ids:
            raise InvalidOperationError(f'Счёт {account_id} уже привязан к клиенту')
        self.account_ids.append(account_id)

    def remove_account(self, account_id):
        '''Убрать ID счёта у клиента.'''
        if account_id not in self.account_ids:
            raise InvalidOperationError(f'Счёт {account_id} не привязан к клиенту')
        self.account_ids.remove(account_id)


class Bank:

    ACCOUNT_TYPES = {
    'basic': BankAccount,
    'savings': SavingsAccount,
    'premium': PremiumAccount,
    'investment': InvestmentAccount,
    }


    def __init__(self,name):
        if not isinstance(name, str) or not name.strip():
            raise InvalidOperationError('Название банка должно быть непустой строкой')
        self.name = name.strip()

        self._clients = {}      
        self._accounts = {}     
        self._max_failed_attempts = 3
        self._allow_operations_24h = False

    def _get_client(self, client_id):
        if client_id not in self._clients:
            raise InvalidOperationError(f'Клиент с ID {client_id} не найден')
        return self._clients[client_id]

    def _get_account(self, account_id):
        if account_id not in self._accounts:
            raise InvalidOperationError(f'Счёт с ID {account_id} не найден')
        return self._accounts[account_id]

    def add_client(self, client):
        '''Добавить клиента в банк.'''
        if not isinstance(client, Client):
            raise InvalidOperationError(f'Ожидается объект Client, получено {type(client).__name__}')
        
        if client.client_id in self._clients:
            raise InvalidOperationError(f'Клиент с ID {client.client_id} уже зарегистрирован')
        
        self._clients[client.client_id] = client
        
        return client.client_id


    def _check_working_hours(self, current_time: time = None):
        if self._allow_operations_24h:
            return
        now = current_time or datetime.now().time()
        if time(0, 0) <= now < time(5, 0):
            raise InvalidOperationError('Операции запрещены с 00:00 до 05:00')

    def open_account(self, client_id, account_type='basic', **kwargs):
        '''Открытие счёта для клиента'''
        self._check_working_hours()

        client = self._get_client(client_id)

        if client.status == Client.STATUS_BLOCKED:
            raise InvalidOperationError(f'Клиент {client.full_name} заблокирован — операция невозможна')

        if account_type not in self.ACCOUNT_TYPES:
            raise InvalidOperationError(f'Неизвестный тип счёта: {account_type}. Доступны: {', '.join(self.ACCOUNT_TYPES.keys())}')

        AccountClass = self.ACCOUNT_TYPES[account_type]
        account = AccountClass(owner=client.full_name, **kwargs)

        client.add_account(account.account_id)
        self._accounts[account.account_id] = account

        return account

    def close_account(self, account_id):
        '''Закрыть счёт.'''
        self._check_working_hours()

        account = self._get_account(account_id)

        if account._status == 'closed':
            raise InvalidOperationError(f'Счёт {account_id} уже закрыт')

        account._status = 'closed'
        return account

    def freeze_account(self, account_id):
        '''Заморозить счёт.'''
        self._check_working_hours()

        account = self._get_account(account_id)

        if account._status == 'closed':
            raise InvalidOperationError(f'Нельзя заморозить закрытый счёт {account_id}')

        if account._status == 'frozen':
            raise InvalidOperationError(f'Счёт {account_id} уже заморожен')

        account._status = 'frozen'
        return account

    def unfreeze_account(self, account_id):
        '''Разморозить счёт.'''
        self._check_working_hours()

        account = self._get_account(account_id)

        if account._status != 'frozen':
            raise InvalidOperationError(f'Счёт {account_id} не заморожен (текущий статус: {account._status})')

        account._status = 'active'
        return account

    def authenticate_client(self, client_id, password):
        '''Проверить пароль. Блокирует клиента после 3 неудач.'''
        client = self._get_client(client_id)

        if client.status == Client.STATUS_BLOCKED:
            raise InvalidOperationError(f'Клиент {client.full_name} заблокирован. ')

        if password != client.password:
            client.failed_attempts += 1
            client.suspicious_actions.append({
                'time': datetime.now().isoformat(),
                'reason': 'Неверный пароль',
                'attempt': client.failed_attempts,
            })
            
            if len(client.suspicious_actions) >= 2:
                client.status = Client.STATUS_SUSPICIOUS

            remaining = self._max_failed_attempts - client.failed_attempts

            if client.failed_attempts >= self._max_failed_attempts:
                client.status = Client.STATUS_BLOCKED
                raise InvalidOperationError(f'Клиент {client.full_name} заблокирован после {self._max_failed_attempts} неудачных попыток')

            raise InvalidOperationError(f'Неверный пароль. Осталось попыток: {remaining}')

        client.failed_attempts = 0
        return True

    def search_accounts(self, owner=None, status=None):
        '''Поиск счетов по владельцу или статусу.'''
        results = []
        for account in self._accounts.values():
            if owner is not None and owner.lower() not in account.owner.lower():
                continue
            if status is not None and account._status != status:
                continue
            results.append(account)
        return results

    def get_total_balance(self, client_id=None):
        '''Общий баланс.'''
        if client_id is not None:
            client = self._get_client(client_id)
            accounts = [self._accounts[aid] for aid in client.account_ids if aid in self._accounts]

        else:
            accounts = list(self._accounts.values())

        return sum(acc._balance for acc in accounts)

    def get_clients_ranking(self):
        '''Рейтинг клиентов по общей сумме балансов.'''
        ranking = []
        for client in self._clients.values():
            total = sum(self._accounts[aid]._balance for aid in client.account_ids if aid in self._accounts)
            ranking.append((client, total))

        ranking.sort(key=lambda pair: pair[1], reverse=True)
        return ranking

if __name__ == '__main__':
    print()
    print('СИСТЕМА BANK — ДЕМОНСТРАЦИЯ')
    print()

    bank = Bank('МойБанк')
    print(f'Банк: {bank.name}')

    c1 = Client('Иванов Иван', 30, 'ivan@mail.ru', '+79991234567', 'pass123')
    c2 = Client('Петров Пётр', 25, 'petr@mail.ru', '+79997654321', 'pass456')

    id1 = bank.add_client(c1)
    id2 = bank.add_client(c2)
    print(f'Клиент 1: {c1.full_name} (ID: {id1})')
    print(f'Клиент 2: {c2.full_name} (ID: {id2})')


    acc1 = bank.open_account(id1, 'basic', balance=1000)
    acc2 = bank.open_account(id1, 'savings', balance=5000, min_balance=1000, monthly_rate=0.05)
    acc3 = bank.open_account(id2, 'premium', balance=10000, overdraft_limit=2000, operation_fee=50)
    acc4 = bank.open_account(id2, 'investment', balance=20000, portfolio={'stocks': 5000, 'bonds': 3000})

    print(f'acc1 basic:      {acc1.account_id} — {acc1._balance} {acc1._currency}')
    print(f'acc2 savings:    {acc2.account_id} — {acc2._balance} {acc2._currency}')
    print(f'acc3 premium:    {acc3.account_id} — {acc3._balance} {acc3._currency}')
    print(f'acc4 investment: {acc4.account_id} — {acc4._balance} {acc4._currency}, портфель: {acc4._portfolio}')

    acc1.deposit(500)
    print(f'acc1 после deposit(500): {acc1._balance}')

    acc2.withdraw(1000)
    print(f'acc2 после withdraw(1000): {acc2._balance}')

    acc3.withdraw(11000)  
    print(f'acc3 после withdraw(11000) : {acc3._balance}')

    print(f'acc4 прогноз роста : {acc4.project_yearly_growth({'stocks': 0.10, 'bonds': 0.04, 'etf': 0.07})}')

    assert bank.authenticate_client(id1, 'pass123') is True
    print('Успешный вход')

    try:
        bank.authenticate_client(id1, 'wrong1')
    except InvalidOperationError as e:
        print(f'Попытка 1: {e}')

    try:
        bank.authenticate_client(id1, 'wrong2')
    except InvalidOperationError as e:
        print(f'Попытка 2 (статус: {c1.status}): {e}')

    try:
        bank.authenticate_client(id1, 'wrong3')
    except InvalidOperationError as e:
        print(f'Попытка 3 (статус: {c1.status}): {e}')

    try:
        bank.authenticate_client(id1, 'pass123')   
    except InvalidOperationError as e:
        print(f'Заблокированный вход: {e}')

    print(f'Подозрительных действий у клиента 1: {len(c1.suspicious_actions)}')


    bank.freeze_account(acc2.account_id)
    print(f'acc2 заморожен: {acc2._status}')

    try:
        acc2.deposit(100)
    except AccountFrozenError as e:
        print(f'Операция на замороженном: {e}')

    bank.unfreeze_account(acc2.account_id)
    print(f'acc2 разморожен: {acc2._status}')

    print(f'По иванов: {len(bank.search_accounts(owner='иванов'))} счетов')
    print(f'По status="active": {len(bank.search_accounts(status='active'))} счетов')
    print(f'По петров + active: {len(bank.search_accounts(owner='петров', status='active'))} счетов')

    print(f'Общий баланс банка: {bank.get_total_balance()}')
    print(f'Баланс клиента 1:   {bank.get_total_balance(id1)}')
    print(f'Баланс клиента 2:   {bank.get_total_balance(id2)}')

    print('\nРейтинг клиентов:')
    for client, total in bank.get_clients_ranking():
        print(f'   {client.full_name}: {total}')


    acc5 = bank.open_account(id2, 'basic', balance=0)
    bank.close_account(acc5.account_id)
    print(f'acc5 закрыт: {acc5._status}')

    try:
        bank.close_account(acc5.account_id)
    except InvalidOperationError as e:
        print(f'Дубль закрытия: {e}')
