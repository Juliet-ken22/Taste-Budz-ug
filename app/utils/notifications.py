from flask_mail import Message
from app import mail, db
from app.models.User import User
from app.models.notification import Notification

def notify_merchant_new_order(order):
    # Assume merchant user exists, fetch their email
    merchant = User.query.filter_by(role='merchant').first()
    if not merchant:
        return

    msg = Message(
        subject="New Order Received",
        recipients=[merchant.email],
        body=f"You have a new order with ID {order.id}. Please check the admin dashboard."
    )
    mail.send(msg)

    # Optional: Log notification in DB
    notification = Notification(
        recipient_id=merchant.id,
        message=f"New order received: Order ID {order.id}"
    )
    db.session.add(notification)
    db.session.commit()
