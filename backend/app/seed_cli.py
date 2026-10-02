from app.database import Base, SessionLocal, engine
from app.main import bootstrap
from app.services.seed import generate_samples


def main():
    Base.metadata.create_all(bind=engine)
    paths = generate_samples()
    print("Generated sample files:")
    for key, path in paths.items():
        print(f"  {key}: {path}")
    result = bootstrap()
    print("Bootstrap result:", result)


if __name__ == "__main__":
    main()
