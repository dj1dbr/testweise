# Add this to server.py

@api_router.delete("/trades/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a specific trade"""
    try:
        # Delete trade
        result = await db.trades.delete_one({"id": trade_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        # Recalculate stats
        open_count = await db.trades.count_documents({"status": "OPEN"})
        closed_count = await db.trades.count_documents({"status": "CLOSED"})
        
        # Calculate P/L
        closed_trades = await db.trades.find({"status": "CLOSED"}).to_list(1000)
        total_pl = sum([t.get('profit_loss', 0) for t in closed_trades])
        
        # Update stats
        await db.stats.update_one(
            {},
            {"$set": {
                "open_positions": open_count,
                "closed_positions": closed_count,
                "total_profit_loss": total_pl,
                "total_trades": open_count + closed_count
            }},
            upsert=True
        )
        
        logger.info(f"Trade {trade_id} deleted, stats updated")
        
        return {"success": True, "message": "Trade deleted"}
    except Exception as e:
        logger.error(f"Error deleting trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))
