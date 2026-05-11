from sqlalchemy.orm import Session
from app.database.models import User, Routine, RoutineItem, Produk
from typing import List, Optional

class RoutineService:
    @staticmethod
    def get_or_create_user(session: Session, email: str, username: str = "") -> User:
        user = session.query(User).filter_by(email=email).first()
        if not user:
            # If username not provided, use email prefix
            if not username:
                username = email.split('@')[0]
            user = User(email=email, username=username, password="EXTERNAL_AUTH") 
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    @staticmethod
    def create_routine(session: Session, user_id: int, name: str, description: str = "") -> Routine:
        routine = Routine(user_id=user_id, name=name, description=description)
        session.add(routine)
        session.commit()
        session.refresh(routine)
        return routine

    @staticmethod
    def get_user_routines(session: Session, user_id: int) -> List[Routine]:
        return session.query(Routine).filter_by(user_id=user_id).all()

    @staticmethod
    def get_routine_details(session: Session, routine_id: int) -> Optional[Routine]:
        return session.query(Routine).filter_by(id=routine_id).first()

    @staticmethod
    def add_item_to_routine(session: Session, routine_id: int, product_id: Optional[int] = None, custom_name: Optional[str] = None, notes: str = ""):
        # Get current max step_order
        count = session.query(RoutineItem).filter_by(routine_id=routine_id).count()
        item = RoutineItem(
            routine_id=routine_id,
            product_id=product_id,
            custom_name=custom_name,
            step_order=count + 1,
            notes=notes
        )
        session.add(item)
        session.commit()
        return item

    @staticmethod
    def remove_item_from_routine(session: Session, item_id: int):
        item = session.query(RoutineItem).filter_by(id=item_id).first()
        if item:
            session.delete(item)
            session.commit()
            return True
        return False

    @staticmethod
    def delete_routine(session: Session, routine_id: int):
        routine = session.query(Routine).filter_by(id=routine_id).first()
        if routine:
            session.delete(routine)
            session.commit()
            return True
        return False
    
    @staticmethod
    def update_item_order(session: Session, item_id: int, new_order: int):
        item = session.query(RoutineItem).filter_by(id=item_id).first()
        if item:
            item.step_order = new_order
            session.commit()
            return True
        return False

    @staticmethod
    def search_products(session: Session, query: str, limit: int = 10) -> List[Produk]:
        return session.query(Produk).filter(Produk.nama.ilike(f"%{query}%")).limit(limit).all()
