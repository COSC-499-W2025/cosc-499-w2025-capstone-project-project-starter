import axios from 'axios';

const API_BASE_URL = 'http://localhost:5001'; // Replace with your backend URL

// Create an Axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;
