import { opensearchClient } from "@/app/lib/opensearch";
import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function POST(request) {
  try {
    const { source = "file", data = null } = await request.json();

    let sessionsData;

    if (source === "file") {
      const filePath = path.join(
        process.cwd(),
        "data",
        "aws_summit_sessions.json"
      );

      if (!fs.existsSync(filePath)) {
        return NextResponse.json(
          {
            success: false,
            error:
              "データファイルが見つかりません: data/aws_summit_sessions.json",
          },
          { status: 404 }
        );
      }

      const fileContent = fs.readFileSync(filePath, "utf-8");
      sessionsData = JSON.parse(fileContent);
    } else if (source === "direct" && data) {
      sessionsData = Array.isArray(data) ? data : [data];
    } else {
      return NextResponse.json(
        {
          success: false,
          error: "有効なデータソースを指定してください",
        },
        { status: 400 }
      );
    }

    console.log(`📁 Importing ${sessionsData.length} AWS Summit sessions...`);

    const results = [];
    const errors = [];

    for (const sessionData of sessionsData) {
      try {
        console.log(
          `📝 Adding session: ${sessionData.session_id} - \${sessionData.title}`
        );

        const result = await opensearchClient.addAwsSummitSession(sessionData);
        results.push({
          session_id: sessionData.session_id,
          title: sessionData.title,
          status: "success",
          result: result._id,
        });

        // OpenSearchの負荷軽減のため少し待機
        await new Promise((resolve) => setTimeout(resolve, 200));
      } catch (error) {
        console.error(
          `❌ Error adding session ${sessionData.session_id}:`,
          error
        );
        errors.push({
          session_id: sessionData.session_id,
          title: sessionData.title,
          status: "error",
          error: error.message,
        });
      }
    }

    return NextResponse.json({
      success: true,
      message: `${results.length}件のセッションデータを投入しました`,
      summary: {
        total: sessionsData.length,
        success: results.length,
        errors: errors.length,
      },
      results,
      errors: errors.length > 0 ? errors : undefined,
    });
  } catch (error) {
    console.error("❌ Data import error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error.message,
        details: error.stack,
      },
      { status: 500 }
    );
  }
}
