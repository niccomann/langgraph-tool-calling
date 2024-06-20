from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_schemadisplay import create_schema_graph

# Crea un motore che punta al file SQLite (qui usiamo un database in memoria)
URI = 'sqlite:///test.db'
engine = create_engine(URI, echo=True)

# Crea una base dichiarativa
Base = declarative_base()

# Definisci i modelli di tabella
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    nickname = Column(String)
    addresses = relationship('Address', back_populates='user')
    orders = relationship('Order', back_populates='user')

class Address(Base):
    __tablename__ = 'addresses'
    id = Column(Integer, primary_key=True)
    email_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='addresses')

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    item = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='orders')

# Crea le tabelle
Base.metadata.create_all(engine)

# Crea una sessione
Session = sessionmaker(bind=engine)
session = Session()

# Crea degli oggetti User
user1 = User(name='John', fullname='John Doe', nickname='johnny')
user2 = User(name='Jane', fullname='Jane Doe', nickname='janie')

# Aggiungi gli utenti alla sessione
session.add(user1)
session.add(user2)
session.commit()

# Crea degli oggetti Address
address1 = Address(email_address='john.doe@example.com', user=user1)
address2 = Address(email_address='jane.doe@example.com', user=user2)

# Aggiungi gli indirizzi alla sessione
session.add(address1)
session.add(address2)
session.commit()

# Crea degli oggetti Order
order1 = Order(item='Laptop', user=user1)
order2 = Order(item='Phone', user=user1)
order3 = Order(item='Tablet', user=user2)

# Aggiungi gli ordini alla sessione
session.add(order1)
session.add(order2)
session.add(order3)
session.commit()

# Query di join per ottenere gli utenti con i loro ordini
results = session.query(User, Order).join(Order).all()
for user, order in results:
    print(user.name, order.item)

# Query di join per ottenere gli utenti con i loro indirizzi
results = session.query(User, Address).join(Address).all()
for user, address in results:
    print(user.name, address.email_address)

# Genera il diagramma ER
metadata = MetaData()
metadata.reflect(bind=engine)

