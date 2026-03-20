import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // -------------------------
  // Agent / Chat
  // -------------------------
  askAgent(payload: {
    session_id: string;
    message: string;
    vehicle_id?: string;
    image_base64?: string;
    user_id?: string;
  }): Observable<any> {
    return this.http.post(`${this.base}/api/agent/ask`, payload);
  }

  // -------------------------
  // Vehicles
  // -------------------------
  getVehicle(code: string): Observable<any> {
    return this.http.get(`${this.base}/api/vehicles/${code}`);
  }

  listVehicles(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/vehicles/`);
  }

  // -------------------------
  // Warranty
  // -------------------------
  checkWarranty(vehicle_id: string, repair_type: string): Observable<any> {
    return this.http.post(`${this.base}/api/warranty/check`, { vehicle_id, repair_type });
  }

  getVehicleWarranties(vehicle_code: string): Observable<any> {
    return this.http.get(`${this.base}/api/warranty/vehicle/${vehicle_code}`);
  }

  // -------------------------
  // Scheduling
  // -------------------------
  getSlots(service_type: string, urgency = 'normal'): Observable<any> {
    return this.http.post(`${this.base}/api/scheduling/slots`, { service_type, urgency });
  }

  bookAppointment(payload: {
    vehicle_code: string;
    service_type: string;
    scheduled_date: string;
    scheduled_time: string;
    technician_code?: string;
    urgency?: string;
    notes?: string;
    warranty_covered?: boolean;
  }): Observable<any> {
    return this.http.post(`${this.base}/api/scheduling/book`, payload);
  }

  getAppointments(vehicle_code: string): Observable<any> {
    return this.http.get(`${this.base}/api/scheduling/appointments/${vehicle_code}`);
  }

  // -------------------------
  // Telematics
  // -------------------------
  getTelematics(vehicle_id: string): Observable<any> {
    return this.http.get(`${this.base}/api/telematics/${vehicle_id}`);
  }

  decodeDTC(codes: string[]): Observable<any> {
    return this.http.post(`${this.base}/api/telematics/decode`, { codes });
  }

  // -------------------------
  // Insurance
  // -------------------------
  getVehicleInsurance(vehicle_code: string): Observable<any> {
    return this.http.get(`${this.base}/api/insurance/${vehicle_code}`);
  }

  getInsurancePlans(): Observable<any> {
    return this.http.get(`${this.base}/api/insurance/plans`);
  }

  // -------------------------
  // User
  // -------------------------
  getCurrentUser(): Observable<any> {
    return this.http.get(`${this.base}/api/user/me`);
  }
}
