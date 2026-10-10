from day1 import (
    BankAccount,
    InvalidOperationError,
    InsufficientFundsError,
)
class SavingsAccount(BankAccount):
    def __init__(self, owner, balance=0, currency='RUB', account_id=None, status='active',min_balance = 100, monthly_rate=0.005):

        if not isinstance(min_balance,(int,float)) or isinstance(min_balance,bool) or min_balance < 0:
            raise InvalidOperationError(f'Минимальный остаток должен быть неотрицательным числом, получено {min_balance}')
        
        if not isinstance(monthly_rate, (int, float)) or isinstance(monthly_rate,bool) or monthly_rate < 0:
            raise InvalidOperationError(
                f'Ставка должна быть неотрицательным числом, получено {monthly_rate}'
            )

        if min_balance > balance:
            raise InvalidOperationError(f'Начальный баланс ({balance}) не может быть меньше минимального остатка ({min_balance})')

        super().__init__(owner, balance, currency, account_id, status)
        self._min_balance = min_balance
        self._monthly_rate = monthly_rate

    def __str__(self):
        return (
            f'{super().__str__()}, '
            f'min_balance={self._min_balance}, '
            f'monthly_rate={self._monthly_rate * 100}%)'
        )

    def apply_monthly_interest(self):
        self._check_active()
        interest = self._balance * self._monthly_rate
        self._balance += interest
        return interest

    def withdraw(self, amount):
        if self._balance - amount < self._min_balance:
            raise InvalidOperationError(
                f'Нельзя снять {amount}: баланс станет {self._balance - amount}, '
                f'а минимум — {self._min_balance}'
            )
        super().withdraw(amount)

    def get_account_info(self):
        '''Вернуть информацию о счёте.'''

        return (f'{super().get_account_info()}, Накопительный счет:'
            f' мин.остаток = {self._min_balance}, '
            f'ставка = {self._monthly_rate * 100}% в месяц')
    
    
class PremiumAccount(BankAccount):
    def __init__(self, owner, balance=0, currency='RUB', account_id=None, status='active',overdraft_limit  = 0,operation_fee = 0):
        
        if (not isinstance(overdraft_limit, (int, float))
                or isinstance(overdraft_limit, bool)
                or overdraft_limit < 0):
            raise InvalidOperationError(
                f'Лимит овердрафта должен быть неотрицательным числом, получено {overdraft_limit}'
            )
        
        if (not isinstance(operation_fee, (int, float))
                or isinstance(operation_fee, bool)
                or operation_fee < 0):
            raise InvalidOperationError(f'Комиссия должна быть неотрицательным числом, получено {operation_fee}')
        
        super().__init__(owner, balance, currency, account_id, status) 

        self._overdraft_limit = overdraft_limit
        self._operation_fee = operation_fee

    def __str__(self):
            return (
                f'{super().__str__()}, '
                f'overdraft_limit={self._overdraft_limit}, '
                f'operation_fee={self._operation_fee})'
            )
    
    def withdraw(self, amount):
        new_balance = self._balance - amount - self._operation_fee
        if new_balance < -self._overdraft_limit:
            raise InsufficientFundsError(
            f'Превышен лимит овердрафта: баланс станет {new_balance}, а минимум — {-self._overdraft_limit}'
        )
        self._check_active()
        self._validate_amount(amount)
        self._balance -= amount + self._operation_fee

    def get_account_info(self):
        return (
        f'{super().get_account_info()}, '
        f'Премиум: овердрафт={self._overdraft_limit}, '
        f'комиссия={self._operation_fee} {self._currency}'
    )

    
class InvestmentAccount(BankAccount):
    ALLOWED_ASSETS = ('stocks', 'bonds', 'etf')

    def __init__(self, owner, balance=0, currency='RUB', account_id=None, status='active',portfolio = None):
        super().__init__(owner, balance, currency, account_id, status)

        if portfolio is None:
            portfolio = {}

        if not isinstance(portfolio,dict):
            raise InvalidOperationError(f'Портфель должен быть словарём, получено {type(portfolio).__name__}')

        for active_type,amount in portfolio.items():
            if active_type not in self.ALLOWED_ASSETS:
                raise InvalidOperationError(
                    f'Недопустимый тип актива: {active_type}. '
                    f'Разрешены: {', '.join(self.ALLOWED_ASSETS)}'
                )
            if (not isinstance(amount, (int, float))
                    or isinstance(amount, bool)
                    or amount <= 0):
                raise InvalidOperationError(
                    f'Сумма актива {active_type} должна быть неотрицательным числом, получено {amount}'
                )

            total_portfolio = sum(portfolio.values())
            if total_portfolio > balance:
                raise InvalidOperationError(f'Портфель ({total_portfolio}) превышает баланс счёта ({balance})')


        self._portfolio = dict(portfolio)

    def __str__(self):
        portfolio_str = ', '.join(
        f'{asset}={amount}' for asset, amount in self._portfolio.items()
        ) or 'пусто'
        return (
        f'{super().__str__()}, '
        f'portfolio=[{portfolio_str}])'
        )

    def withdraw(self, amount):
        '''Снятие со счёта'''
        super().withdraw(amount)

    def project_yearly_growth(self, growth_rates):
        '''Прогноз годового прироста портфеля.'''
        if not isinstance(growth_rates, dict):
            raise InvalidOperationError(f'growth_rates должен быть словарём, получено {type(growth_rates).__name__}')

        growth = {}
        for active_type,amount in self._portfolio.items():
            if active_type not in growth_rates:
                raise InvalidOperationError(f'Нет ставки для актива {active_type} в growth_rates')
            
            rate = growth_rates[active_type]
            if (not isinstance(rate, (int, float))
                or isinstance(rate, bool)
                or rate < 0):
                raise InvalidOperationError(f'Ставка для {active_type} должна быть неотрицательным числом, получено {rate}')

            growth[active_type] = amount * rate

        growth['total'] = sum(growth.values())
        return  growth

    def get_account_info(self):
        portfolio_str = ', '.join(
            f'{active_type}={amount}' for active_type, amount in self._portfolio.items()
        ) or 'пусто'
        return (
            f'{super().get_account_info()}, '
            f'Портфель: [{portfolio_str}]'
        )

if __name__ == '__main__':
    print()
    print('1. SAVINGS ACCOUNT')
    print()
    s = SavingsAccount('Иван', balance=1000, min_balance=200, monthly_rate=0.05)
    print(s)
    print(s.get_account_info())

    interest = s.apply_monthly_interest()
    print(f'Проценты: начислено {interest}, баланс = {s._balance}')

    s.withdraw(500)
    print(f'Снятие 500: баланс = {s._balance}')

    try:
        s.withdraw(400)  
        print('Должно было упасть')
    except InvalidOperationError as e:
        print(f'Ошибка: {e}')
        print(f'Баланс не изменился: {s._balance}')

    print()
    print('2. PREMIUM ACCOUNT')
    print()
    p = PremiumAccount('Олег', balance=1000, overdraft_limit=500, operation_fee=10)
    print(p)
    print(p.get_account_info())

    p.withdraw(300)
    print(f'Снятие 300 +комиссия 10: баланс = {p._balance}')

    p.withdraw(1000)
    print(f'Снятие 1000 в овердрафт:   баланс = {p._balance}')

    try:
        p.withdraw(300)   
        print('Должно было упасть')
    except InsufficientFundsError as e:
        print(f'Ошибка: {e}')

    p.deposit(500)
    print(f'Пополнение 500 без комиссии: баланс = {p._balance}')

    
    print()
    print('3. INVESTMENT ACCOUNT')
    print()

    inv = InvestmentAccount(
        'Анна',
        balance=10000,
        portfolio={'stocks': 3000, 'bonds': 2000, 'etf': 1000},
    )
    print(inv)
    print(inv.get_account_info())

    rates = {'stocks': 0.10, 'bonds': 0.04, 'etf': 0.07}
    growth = inv.project_yearly_growth(rates)
    print(f'Прогноз роста: {growth}')

    inv.withdraw(500)
    print(f'Снятие 500: баланс = {inv._balance}')
    print(f'Портфель после снятия: {inv._portfolio}')

    print()
    print('4. ТЕСТ ВАЛИДАЦИИ ИНВЕСТИЦИОННОГО СЧЁТА')

    try:
        InvestmentAccount("Тест", balance=100, portfolio={"stocks": 1_000_000})
        print(" Портфель > баланс прошёл")
    except InvalidOperationError as e:
        print(f" Портфель > баланс: {e}")

    try:
        InvestmentAccount("Тест", balance=10000, portfolio={"stocks": 0})
        print(" Ноль прошёл")
    except InvalidOperationError as e:
        print(f" Ноль: {e}")

    try:
        InvestmentAccount("Тест", balance=10000, portfolio={"stocks": -500})
        print(" Отрицательная сумма прошла")
    except InvalidOperationError as e:
        print(f" Отрицательная сумма: {e}")

    acc = InvestmentAccount("Тест", balance=10000, portfolio={"stocks": 10000})
    print(f" Портфель == баланс: {acc._portfolio}")

    acc = InvestmentAccount("Тест", balance=10000, portfolio={"stocks": 5000})
    print(f" Портфель < баланс: {acc._portfolio}")    