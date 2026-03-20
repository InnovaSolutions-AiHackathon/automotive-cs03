import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-scheduling',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scheduling.html',
  styleUrl: './scheduling.scss',
})
export class Scheduling implements OnInit {
  vehicles: any[] = [];
  slots: any[] = [];

  vehicleCode = '';
  serviceType = '';
  urgency = 'normal';
  notes = '';
  selectedSlot: any = null;

  loadingVehicles = true;
  loadingSlots = false;
  booking = false;
  booked = false;
  error = '';

  serviceTypes = [
    { label: 'Oil Change',        value: 'general' },
    { label: 'Engine Check',      value: 'engine' },
    { label: 'Battery / Electrical', value: 'electrical' },
    { label: 'Brake Service',     value: 'brakes' },
    { label: 'AC / HVAC',        value: 'ac' },
    { label: 'Suspension',        value: 'suspension' },
    { label: 'Full Diagnostics',  value: 'diagnostics' },
  ];

  urgencyOptions = [
    { label: 'Normal (3+ days)',   value: 'normal' },
    { label: 'High Priority (2 days)', value: 'high' },
    { label: 'Critical (ASAP)',    value: 'critical' },
  ];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listVehicles().subscribe({
      next: (list) => {
        this.vehicles = list;
        this.loadingVehicles = false;
      },
      error: () => {
        this.error = 'Failed to load vehicles';
        this.loadingVehicles = false;
      },
    });
  }

  findSlots(): void {
    if (!this.serviceType) return;
    this.loadingSlots = true;
    this.slots = [];
    this.selectedSlot = null;
    this.booked = false;

    this.api.getSlots(this.serviceType, this.urgency).subscribe({
      next: (res) => {
        this.slots = res.slots ?? [];
        this.loadingSlots = false;
      },
      error: () => {
        this.error = 'Failed to load slots';
        this.loadingSlots = false;
      },
    });
  }

  selectSlot(slot: any): void {
    this.selectedSlot = slot;
  }

  confirmBooking(): void {
    if (!this.vehicleCode || !this.selectedSlot) {
      this.error = 'Please select a vehicle and a time slot.';
      return;
    }
    this.booking = true;
    this.error = '';

    this.api.bookAppointment({
      vehicle_code:    this.vehicleCode,
      service_type:    this.serviceType,
      scheduled_date:  this.selectedSlot.date,
      scheduled_time:  this.selectedSlot.time,
      technician_code: this.selectedSlot.technician_code,
      urgency:         this.urgency,
      notes:           this.notes,
    }).subscribe({
      next: () => {
        this.booked = true;
        this.booking = false;
        this.slots = [];
        this.selectedSlot = null;
      },
      error: () => {
        this.error = 'Booking failed. Please try again.';
        this.booking = false;
      },
    });
  }
}
