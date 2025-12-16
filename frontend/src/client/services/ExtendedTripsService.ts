import { OpenAPI } from "../core/OpenAPI";
import { request as __request } from "../core/request";

// Define types to fix 'unknown' errors
export interface UploadResponse {
  success: boolean;
  summary: {
    total_rows: number;
    successful: number;
    failed: number;
  };
}

export interface OptimizationResponse {
  message: string;
  details: {
    batch_id: string;
    trips_optimized: number;
    km_saved: number;
  };
}

export interface KPIResponse {
  date: string;
  savings: {
    km_saved: number;
    fuel_saved_liters: number;
    co2_saved_kg: number;
    cost_saved_usd: number;
  };
  summary: {
    trips_contributed: number;
    vehicles_used: number;
  };
}

export class ExtendedTripsService {
  // 1. Upload Trip File
  public static uploadTrips(formData: FormData): Promise<UploadResponse> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/trips/upload",
      body: formData,
    });
  }

  // 1b. Create Trip From Map (multipart/form-data)
  public static createTripFromMap(formData: FormData): Promise<any> {
    return __request(OpenAPI, {
      method: "POST",
      url: "/api/v1/trips/map/create",
      body: formData,
    });
  }

  // 2. Get Trips for Date
  public static getTripsByDate(
    date: string,
    status?: string
  ): Promise<{ data: any[]; count: number }> {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/trips/date/${date}`,
      query: { status },
    });
  }

  // 3. Get Map Data
  public static getMapData(date: string): Promise<any> {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/trips/map/${date}`,
    });
  }

  // 4. Trigger Optimization
  public static optimize(date: string): Promise<OptimizationResponse> {
    return __request(OpenAPI, {
      method: "POST",
      url: `/api/v1/trips/optimize/${date}`,
      query: { optimization_type: "cross_company" },
    });
  }

  // 5. Get KPIs
  public static getKPIs(date: string): Promise<KPIResponse> {
    return __request(OpenAPI, {
      method: "GET",
      url: `/api/v1/trips/kpis/${date}`,
    });
  }
}
