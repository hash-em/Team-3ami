const express = require('express');
const router  = express.Router();
const { getAll, getById, getSummary } = require('../services/historyStore');

/**
 * GET /api/history
 * Query params: page (default 1), limit (default 20)
 * Returns paginated prediction history + overall summary stats.
 */
router.get('/', (req, res) => {
  const page  = Math.max(1, parseInt(req.query.page)  || 1);
  const limit = Math.min(100, Math.max(1, parseInt(req.query.limit) || 20));

  const result = getAll({ page, limit });
  result.summary = getSummary();
  res.json(result);
});

/**
 * GET /api/history/:id
 * Returns a single history entry including full client snapshot.
 */
router.get('/:id', (req, res) => {
  const entry = getById(req.params.id);
  if (!entry) return res.status(404).json({ error: 'History entry not found.' });
  res.json(entry);
});

module.exports = router;
