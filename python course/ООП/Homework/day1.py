from abc import ABC, abstractmethod
import uuid

class BankAccountError(Exception):
    '''Класс базового исключения для банковских ошибок.'''
    pass

class AccountFrozenError(BankAccountError):
    '''Операция над замороженным счётом.'''
    pass


class AccountClosedError(BankAccountError):
    '''Операция над закрытым счётом.'''
    pass


class InvalidOperationError(BankAccountError):
    '''Некорректная операция'''
    pass


class InsufficientFundsError(BankAccountError):
    '''Недостаточно средств на счёте для операции.'''
    pass


class AbstractAccount(ABC):
    '''Абстрактный банковский счёт'''

    @abstractmethod
    def deposit(self, amount):
        '''Пополнить счёт.'''
        pass

    
    @abstractmethod
    def withdraw(self, amount):
        '''Снять деньги со счёта.'''
        pass

    @abstractmethod
    def get_account_info(self):
        '''Вернуть информацию о счёте.'''
        pass


class BankAccount(AbstractAccount):

    ALLOWED_CURRENCIES = ('RUB', 'USD', 'EUR', 'KZT', 'CNY')
    ALLOWED_STATUSES = ('active', 'frozen', 'closed')

    def __init__(self,owner,balance = 0,currency = 'RUB',account_id = None,status = 'active'):

        if not isinstance(owner, str) or not owner.strip():
            raise InvalidOperationError('Владелец должен быть непустой строкой')
        self.owner = owner.strip()

        if not isinstance(balance, (int, float)):
            raise InvalidOperationError(f'Баланс должен быть числом, получено {type(balance).__name__}')
        if balance < 0:
            raise InvalidOperationError(f'Баланс не может быть отрицательным, получено {balance}')
        self._balance = balance

        if status not in self.ALLOWED_STATUSES:
            raise InvalidOperationError(f'Недопустимый статус: {status}')
        self._status = status

        if currency not in self.ALLOWED_CURRENCIES:
            raise InvalidOperationError(
                f'Недопустимая валюта: {currency}. '
                f'Разрешены: {', '.join(self.ALLOWED_CURRENCIES)}'
            )
        self._currency = currency

        if account_id is None:
            self.account_id = str(uuid.uuid4())[:8]
        else:
            self.account_id = account_id
        
    def __str__(self):
        short_id = str(self.account_id)[-4:] 
        return (
            f'{self.__class__.__name__}(owner={self.owner}, '
            f'id=...{short_id}, '
            f'status={self._status}, '
            f'balance={self._balance} {self._currency}'
        )

    def _check_active(self):
        if self._status == 'frozen':
            raise AccountFrozenError(f'Счет {self.account_id} заморожен')
        elif self._status == 'closed':
            raise AccountClosedError(f'Счет {self.account_id} закрыт')                    

    def _validate_amount(self,amount):
        if isinstance(amount, bool) or not isinstance(amount,(float,int)):
            raise InvalidOperationError(f'Сумма должна быть числом, получено {amount}')
        if amount <= 0:
           raise InvalidOperationError(f'Сумма должна быть положительной, получено {amount}')
        
    def deposit(self, amount):
        self._check_active()
        self._validate_amount(amount)
        self._balance += amount

    def withdraw(self, amount):
        self._check_active()
        self._validate_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError('Недостаточно средств на счёте для операции')
        self._balance -= amount

    def get_account_info(self):
        '''Вернуть информацию о счёте.'''
        return f'Счет {self.account_id} со статусом {self._status} имеет {self._balance} {self._currency}'


if __name__ == '__main__':

    # 1. Создание
    acc = BankAccount('Иван', 1000, 'RUB')
    print('Создан:', acc)

    # 2. Пополнение
    acc.deposit(500)
    assert acc._balance == 1500
    print('Пополнение:', acc._balance)

    # 3. Снятие
    acc.withdraw(200)
    assert acc._balance == 1300
    print('Снятие:', acc._balance)

    # 4. Недостаточно средств
    try:
        acc.withdraw(99999)
        print('Не упало')
    except InsufficientFundsError as e:
        print(f'InsufficientFundsError: {e}')

    # 5. Плохая сумма
    for bad in [0, -100, 'abc']:
        try:
            acc.deposit(bad)
            print(f'Не упало на {bad}')
        except InvalidOperationError:
            pass
    print('Валидация суммы работает')

    # 6. Замороженный счёт
    frozen = BankAccount('Пётр', 500, status='frozen')
    try:
        frozen.deposit(100)
        print('Замороженный не заблокирован')
    except AccountFrozenError as e:
        print(f'AccountFrozenError: {e}')

    # 7. Закрытый счёт
    closed = BankAccount('Анна', 0, status='closed')
    try:
        closed.deposit(100)
        print('Закрытый не заблокирован')
    except AccountClosedError as e:
        print(f'AccountClosedError: {e}')

    # 8. Плохая валюта
    try:
        BankAccount('Иван', currency='rub')
        print('rub прошёл')
    except InvalidOperationError as e:
        print(f'Строгая валюта: {e}')
