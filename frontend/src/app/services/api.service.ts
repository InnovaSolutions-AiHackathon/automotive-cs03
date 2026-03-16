import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;   // http://localhost:8000

  constructor(private http: HttpClient) {}

  // Agent
  askAgent(payload: {
    session_id: string; message: string;
    vehicle_id?: string; image_base64?: string
  }): Observable<any> {
    return this.http.post(`${this.base}/api/agent/ask`, payload);
  }

  // Vehicles
  getVehicle(code: string): Observable<any> {
    return this.http.get(`${this.base}/api/vehicles/${code}`);
  }

  listVehicles(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/vehicles/`);
  }

  // Warranty
  checkWarranty(vehicle_id: string, repair_type: string): Observable<any> {
    return this.http.post(`${this.base}/api/warranty/check`,
      { vehicle_id, repair_type });
  }

  // Scheduling
  getSlots(service_type: string, urgency = 'normal'): Observable<any> {
    return this.http.post(`${this.base}/api/scheduling/slots`,
      { service_type, urgency });
  }

  // Telematics
  getTelematics(vehicle_id: string): Observable<any> {
    return this.http.get(`${this.base}/api/telematics/${vehicle_id}`);
  }
}