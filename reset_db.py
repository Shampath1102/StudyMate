from flask_app import app, db
import os
import time

def reset_database():
    with app.app_context():
        try:
            # Close all sessions and connections
            db.session.remove()
            db.engine.dispose()
            
            # Wait a moment for connections to close
            time.sleep(1)
            
            # Remove the old database
            db_path = "c:/Users/rupa1/OneDrive/Desktop/EXAMPREPFINAL/instance/database.db"
            if os.path.exists(db_path):
                os.remove(db_path)
                print("Old database removed successfully")
            
            # Create new database with updated schema
            db.create_all()
            print("New database created successfully")
            
        except PermissionError:
            print("Error: Database is still in use. Please close all applications and try again.")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    reset_database()