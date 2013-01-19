#pragma once

#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/power.h>
#include <avr/interrupt.h>

#if defined (CDC_MODE)
#include "Descriptors_cdc.h"
#else
#include "Descriptors_custom.h"
#endif

#include "usb.h"

/* Function Prototypes: */
void SetupHardware(void);

bool EVENT_USB_Device_ControlRequest(USB_Request_Header_t* req);

