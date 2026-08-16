from app import (
    app,
    db,
    User,
    Clan,
    ClanJoinRequest,
    ClanSearchChatMessage,
    ClanChatMessage,
    TerritoryAdminChatMessage,
    PvPArenaPresence,
    PvPArenaChatMessage,
    PvPDuelChallenge,
    PvPDuel,
    UserTerritoryStats,
    UserShopPurchase,
    UserEquipment,
    ActiveItemBuff,
    TerritoryRegionState,
)


USER_IDS = []


def main() -> None:
    with app.app_context():
        print(f"Начинаю удаление пользователей {USER_IDS} и всех связанных записей...")

        # --- PvP дуэли и вызовы ---
        PvPDuelChallenge.query.filter(
            (PvPDuelChallenge.challenger_id.in_(USER_IDS))
            | (PvPDuelChallenge.defender_id.in_(USER_IDS))
        ).delete(synchronize_session=False)

        PvPDuel.query.filter(
            (PvPDuel.challenger_id.in_(USER_IDS))
            | (PvPDuel.defender_id.in_(USER_IDS))
            | (PvPDuel.current_turn_user_id.in_(USER_IDS))
            | (PvPDuel.winner_id.in_(USER_IDS))
        ).delete(synchronize_session=False)

        # --- Присутствие и чат PvP арены ---
        PvPArenaPresence.query.filter(
            PvPArenaPresence.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        PvPArenaChatMessage.query.filter(
            PvPArenaChatMessage.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        # --- Клановые сущности, завязанные на user_id ---
        ClanJoinRequest.query.filter(
            ClanJoinRequest.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        ClanSearchChatMessage.query.filter(
            ClanSearchChatMessage.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        ClanChatMessage.query.filter(
            ClanChatMessage.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        TerritoryAdminChatMessage.query.filter(
            TerritoryAdminChatMessage.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        # --- Статистика по территории ---
        UserTerritoryStats.query.filter(
            UserTerritoryStats.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        # --- Активные бафы от предметов ---
        ActiveItemBuff.query.filter(
            ActiveItemBuff.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        # --- Инвентарь и экипировка ---
        UserEquipment.query.filter(
            UserEquipment.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        UserShopPurchase.query.filter(
            UserShopPurchase.user_id.in_(USER_IDS)
        ).delete(synchronize_session=False)

        # --- Кланы, владельцами которых являются эти пользователи ---
        clans_to_delete = Clan.query.filter(Clan.owner_id.in_(USER_IDS)).all()
        clan_ids_to_delete = [c.id for c in clans_to_delete]

        if clan_ids_to_delete:
            # Сначала снимаем владение областями у этих кланов
            TerritoryRegionState.query.filter(
                TerritoryRegionState.owner_clan_id.in_(clan_ids_to_delete)
            ).update(
                {TerritoryRegionState.owner_clan_id: None},
                synchronize_session=False,
            )

        for clan in clans_to_delete:
            db.session.delete(clan)

        # --- Непосредственно пользователи ---
        users_to_delete = User.query.filter(User.id.in_(USER_IDS)).all()
        for user in users_to_delete:
            db.session.delete(user)

        db.session.commit()
        print("Готово: пользователи и все связанные записи удалены.")


if __name__ == "__main__":
    main()

