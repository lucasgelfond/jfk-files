import express from "express";
import dotenv from "dotenv";

dotenv.config();

const IS_PRODUCTION = !process.env.IS_DEV;
const BASE_URL = IS_PRODUCTION
  ? "http://anythingllm.railway.internal"
  : "https://anythingllm-production-047a.up.railway.app";
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

    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: "Failed to proxy chat request" });
  }
});

export default router;
