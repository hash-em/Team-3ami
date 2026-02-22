const express = require('express');
const router  = express.Router();
const { predictSingle }   = require('../services/predictionService');
const { addEntry }        = require('../services/historyStore');

/**
 * POST /api/predict-single
 *
 * Body: JSON object with client feature fields.
 * Returns the predicted Purchased_Coverage_Bundle (0–9).
 *
 * Example request body:
 * {
 *   "User_ID": "USR_001",
 *   "Estimated_Annual_Income": 75000,
 *   "Adult_Dependents": 1,
 *   ...
 * }
 */
router.post('/', async (req, res, next) => {
  try {
    const row = req.body;

    if (!row || Object.keys(row).length === 0) {
      return res.status(400).json({
        error: 'Request body is empty. Send client feature data as JSON.',
      });
    }

    // Auto-assign User_ID if missing
    if (!row.User_ID) {
      row.User_ID = `USR_${Date.now()}`;
    }

    const t0         = Date.now();
    const prediction = await predictSingle(row);
    const durationMs = Date.now() - t0;

    const entry = addEntry({ clientData: row, prediction, durationMs });

    res.json({
      status: 'success',
      prediction,
      durationMs,
      historyId: entry.id,
    });
  } catch (err) {
    next(err);
  }
});

module.exports = router;
