from sqlalchemy import create_engine, MetaData

DATABASE_URL = "mysql+mysqlconnector://admin:scalabledatabase1@database-1.cedp9b7wrci2.us-east-1.rds.amazonaws.com:3306/database-1"

engine = create_engine(DATABASE_URL, echo=True)  # <- This shows SQL commands

metadata = MetaData()
metadata.create_all(engine)
print("Tables created successfully.")
