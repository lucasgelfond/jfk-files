import express from "express";
import dotenv from "dotenv";

dotenv.config();

const BASE_URL = process.env.BASE_URL;
const router = express.Router();

router.post("/", async (req, res) => {
  try {
    const response = await fetch(`${BASE_URL}/api/v1/workspace/jfk/chat`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.ANYTHING_LLM_AUTHORIZATION}`,
      },
      body: JSON.stringify(req.body),
    });

    console.log({ req });

    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: "Failed to proxy chat request" });
  }
});

export default router;
