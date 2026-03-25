from app import create_app, db
from app.models.User import User
from werkzeug.security import generate_password_hash

def fix_null_passwords():
    app = create_app()
    with app.app_context():
        # Correct query syntax
        customers = db.session.query(User).filter(
            User.role == 'customer',
            User.password_hash.is_(None)
        ).all()

        for customer in customers:
            customer.password_hash = generate_password_hash('TempPass123!')
            db.session.add(customer)
        
        db.session.commit()
        print(f"Updated {len(customers)} customer accounts")

if __name__ == '__main__':
    fix_null_passwords()