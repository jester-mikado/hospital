import models
from database import engine

models.Base.metadata.create_all(bind=engine)

print("Tables created successfully")