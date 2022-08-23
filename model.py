import peewee
import datetime

sqlite_db = peewee.SqliteDatabase('bot_db', pragmas={
    'journal_mode': "wal",
    'cache_size': -1024 * 64
})


class BaseModel(peewee.Model):
    class Meta:
        database = sqlite_db
        order_by = 'id'


class User(BaseModel):
    id = peewee.BigIntegerField(primary_key=True, unique=True)
    telegram_id = peewee.BigIntegerField(unique=True)
    name = peewee.CharField(max_length=70)
    lessons_quant = peewee.IntegerField(default=0)
    request_date = peewee.DateTimeField(default=datetime.datetime.now)
    confirmed = peewee.BooleanField(default=False)
    blocked = peewee.BooleanField(default=False)
    block_date = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = 'users'


class Notification(BaseModel):
    user = peewee.ForeignKeyField(User)
    notification_date = peewee.DateTimeField()
    performed = peewee.BooleanField(default=False)
    canceled = peewee.BooleanField(default=False)

    class Meta:
        db_table = 'notifications'


if __name__ == "__main__":
    sqlite_db.create_tables([User, Notification])
