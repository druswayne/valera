from app import (
    app,
    db,
    User,
    ShopItem,
    UserShopPurchase,
    SHOP_CONTEXT_TERRITORY,
    DEFAULT_TERRITORY_SHOP_ITEM_NAMES,
)


def grant_default_for_user(user: User) -> int:
    items = (
        ShopItem.query.filter(
            ShopItem.shop_context == SHOP_CONTEXT_TERRITORY,
            ShopItem.name.in_(DEFAULT_TERRITORY_SHOP_ITEM_NAMES),
        ).all()
    )
    if not items:
        return 0
    existing_ids = {
        p.shop_item_id
        for p in UserShopPurchase.query.filter_by(user_id=user.id).all()
    }
    created = 0
    for item in items:
        if item.id in existing_ids:
            continue
        db.session.add(UserShopPurchase(user_id=user.id, shop_item_id=item.id))
        created += 1
    return created


def main():
    with app.app_context():
        users = User.query.filter(User.is_admin == False).all()
        total_created = 0
        for u in users:
            created = grant_default_for_user(u)
            if created:
                print(f"Пользователь {u.id} ({u.username}): добавлено {created} предметов")
                total_created += created
        db.session.commit()
        print(f"Готово, всего создано покупок: {total_created}")


if __name__ == "__main__":
    main()

