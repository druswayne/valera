"""
Снять всё снаряжение битвы за территорию (таблица user_equipment) у всех пользователей.
Покупки в инвентаре не трогаются — удаляются только записи «надето».

Запуск из корня проекта:
  python unequip_all_territory_equipment.py
"""

from app import app, db, User, UserEquipment


def main() -> None:
    with app.app_context():
        count = UserEquipment.query.count()
        if count == 0:
            print("Записей экипировки нет, нечего снимать.")
            return

        UserEquipment.query.delete(synchronize_session=False)
        db.session.commit()
        print(f"Снято записей экипировки: {count}")

        adjusted = 0
        for u in User.query.all():
            u.ensure_energy_refill()
            if u.current_energy is not None and u.current_energy > u.energy:
                u.current_energy = u.energy
                adjusted += 1
        db.session.commit()
        if adjusted:
            print(f"Подрезана текущая энергия до нового максимума у пользователей: {adjusted}")
        print("Готово.")


if __name__ == "__main__":
    main()
