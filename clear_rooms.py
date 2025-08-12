from app.redis_model import Room, Message

def instant_delete_all_rooms():
    rooms = Room.find().all()
    for room in rooms:
        messages = Message.find(Message.room_id == room.pk).all()
        for msg in messages:
            msg.delete()
        room.delete()
        print(f"Deleted room {room.pk} and its messages")

if __name__ == "__main__":
    instant_delete_all_rooms()
