const express = require('express');
const cors = require('cors');
const mongoose = require('mongoose');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

mongoose.connect(process.env.MONGO_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true
}).then(() => console.log('MongoDB connected'))
  .catch(err => console.error('MongoDB connection error:', err));

const Trip = mongoose.model('Trip', new mongoose.Schema({
  destination: String,
  days: Number,
  preferences: Object,
  radius: Number,
  createdAt: { type: Date, default: Date.now }
}));

app.post('/plan', async (req, res) => {
  try {
    const { destination, days, preferences, radius } = req.body;
    const trip = new Trip({ destination, days, preferences, radius });
    await trip.save();

    const aiRes = await axios.post('http://localhost:8000/generate-itinerary', {
      destination,
      days,
      preferences,
      radius
    });

    res.json(aiRes.data);
  } catch (error) {
    console.error('Error generating itinerary:', error);
    res.status(500).json({ error: 'Failed to generate itinerary' });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
