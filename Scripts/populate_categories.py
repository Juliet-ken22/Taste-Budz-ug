import click
from flask.cli import with_appcontext
from app import db
from app.models.MenuItem_Toppings import MenuItem, Category

@click.command('populate-categories')
@with_appcontext
def populate_categories_command():
    """Populates the Category table from existing MenuItem categories."""
    print("Populating categories...")
    
    unique_categories = db.session.query(MenuItem.category).distinct().all()
    
    for category_name_tuple in unique_categories:
        category_name = category_name_tuple[0]
        existing_category = Category.query.filter_by(name=category_name).first()
        
        if not existing_category:
            new_category = Category(name=category_name)
            db.session.add(new_category)
            print(f"Added category: {category_name}")
    
    db.session.commit()
    print("Categories populated successfully!")