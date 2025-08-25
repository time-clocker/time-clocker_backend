from sqlalchemy.orm import declarative_base
Base = declarative_base()

from app.models.employee import Employee  # noqa
from app.models.time_entry import TimeEntry  # noqa
from app.models.pay_rule import PayRule  # noqa
